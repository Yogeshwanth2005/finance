from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from lib.auth import get_current_user
from lib.db import db
from lib.chat_context import HISTORY_LIMIT, SCOPE_RULES, build_retrieval_query, cited_titles, format_history
from lib.llm import llm_configured, stream_answer
from lib.rag import retrieve, retrieve_across_documents
from models.profile import ProfileInput
from models.rag import ChatMessageRecord, ChatQuestion
from routers.profile import _analysis

router = APIRouter(prefix="/chat", tags=["chat"])

COMPARISON_WORDS = (
    "compare", "comparison", " vs ", " versus ", "difference between", "better than",
    "तुलना", "मुकाबला", "పోల్చ", "పోలిక", "ஒப்பிட", "ஒப்பீடு",
)
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil"}
GENERIC_TITLE_WORDS = {
    "insurance", "policy", "plan", "term", "health", "life", "cover", "coverage",
    "secure", "family", "benefit", "benefits", "document", "product", "brochure",
}


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _fallback(question: str, profile: ProfileInput | None, sources: list[dict], language: str) -> str:
    if not sources:
        return {
            "hi": "संबंधित बीमा दस्तावेज़ एडमिन द्वारा इंडेक्स होने के बाद ही मैं सटीक उत्तर दे सकता हूँ। तब तक मैं लाभ या अपवाद नहीं गढ़ूँगा।",
            "te": "సంబంధిత బీమా పత్రాలను అడ్మిన్ ఇండెక్స్ చేసిన తర్వాత మాత్రమే నేను ఖచ్చితంగా సమాధానం ఇవ్వగలను. అప్పటి వరకు ప్రయోజనాలు లేదా మినహాయింపులను ఊహించను.",
            "ta": "தொடர்புடைய காப்பீட்டு ஆவணங்களை நிர்வாகி அட்டவணைப்படுத்திய பிறகே துல்லியமாக பதிலளிக்க முடியும். அதுவரை நன்மைகள் அல்லது விலக்குகளை கற்பனை செய்ய மாட்டேன்.",
        }.get(language, "I can answer precisely once an admin indexes the relevant insurance-plan documents. Until then, I will not invent policy benefits or exclusions.")
    analysis = _analysis(profile) if profile else None
    context = sources[0]["text"][:260]
    gap_value = f"₹{analysis.term_gap_crore:.2f} Cr" if analysis else "—"
    return {
        "hi": f"इंडेक्स किए गए बीमा दस्तावेज़ से: {context} आपकी अनुमानित टर्म कमी {gap_value} है। खरीदने से पहले नवीनतम पॉलिसी शेड्यूल और अपवाद सत्यापित करें।",
        "te": f"ఇండెక్స్ చేసిన బీమా పత్రం నుండి: {context} మీ అంచనా టర్మ్ లోటు {gap_value}. కొనుగోలు ముందు తాజా పాలసీ షెడ్యూల్ మరియు మినహాయింపులను ధృవీకరించండి.",
        "ta": f"அட்டவணைப்படுத்தப்பட்ட காப்பீட்டு ஆவணத்திலிருந்து: {context} உங்கள் மதிப்பிடப்பட்ட டெர்ம் இடைவெளி {gap_value}. வாங்கும் முன் சமீபத்திய பாலிசி அட்டவணை மற்றும் விலக்குகளை சரிபார்க்கவும்.",
    }.get(language, f"From the indexed insurance documents: {context} Your current estimated term gap is {gap_value}. Verify the latest policy schedule and exclusions before buying.")


def _significant_words(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", value.lower()) if len(word) >= 4 and word not in GENERIC_TITLE_WORDS}


def _matching_document_ids(question: str, documents: list[dict]) -> list[str]:
    normalized = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    question_words = _significant_words(question)
    matches: list[str] = []
    for document in documents:
        title = document.get("title", "")
        normalized_title = " ".join(re.findall(r"[a-z0-9]+", title.lower()))
        title_words = _significant_words(title)
        exact_title = bool(normalized_title and normalized_title in normalized)
        distinctive_overlap = question_words & title_words
        if exact_title or distinctive_overlap:
            matches.append(document["id"])
    return matches


def _general_profile_answer(question: str, profile: ProfileInput | None, language: str) -> str:
    if not profile:
        return {
            "hi": "टर्म इंश्योरेंस मुख्यतः आप पर निर्भर लोगों के लिए आय की भरपाई है। किसी विशेष प्लान का प्रचार किए बिना व्यक्तिगत उत्तर पाने के लिए अपना परिवार प्रोफ़ाइल पूरा करें।",
            "te": "టర్మ్ ఇన్సూరెన్స్ ప్రధానంగా మీపై ఆధారపడిన వారికి ఆదాయ భర్తీ. ఏ ప్రత్యేక ప్లాన్‌ను ప్రోత్సహించకుండా వ్యక్తిగత వివరణ కోసం కుటుంబ ప్రొఫైల్ పూర్తి చేయండి.",
            "ta": "டெர்ம் காப்பீடு என்பது உங்களைச் சார்ந்தவர்களுக்கான வருமான மாற்றீடு. குறிப்பிட்ட திட்டத்தை விளம்பரப்படுத்தாமல் தனிப்பட்ட விளக்கம் பெற குடும்ப விவரத்தை முடிக்கவும்.",
        }.get(language, "Term insurance is primarily income replacement for people who depend on you. Complete your family profile for a personalized explanation without promoting any particular plan.")
    analysis = _analysis(profile)
    lower = question.lower()
    is_critical = any(value in lower for value in ("critical illness", "critical disease", "गंभीर बीमारी", "తీవ్రమైన అనారోగ్యం", "தீவிர நோய்"))
    is_term = any(value in lower for value in ("term", "life insurance", "टर्म", "जीवन बीमा", "టర్మ్", "జీవిత బీమా", "டெர்ம்", "ஆயுள் காப்பீடு"))
    is_health = any(value in lower for value in ("health", "medical", "स्वास्थ्य", "चिकित्सा", "ఆరోగ్య", "వైద్య", "சுகாதார", "மருத்துவ"))
    if is_critical:
        if language == "hi":
            return f"क्रिटिकल इलनेस लाभ टर्म इंश्योरेंस से अलग है: कवर की गई बीमारी के निदान पर नियमों और अपवादों के अधीन एकमुश्त राशि मिल सकती है। आपकी वार्षिक घरेलू आय ₹{analysis.annual_household_income:,.0f}, आपात बचत ₹{profile.emergency_savings:,.0f}, और आपात फंड की कमी ₹{analysis.emergency_gap:,.0f} है। निर्णय से पहले नियोक्ता लाभ, पारिवारिक चिकित्सा इतिहास, मौजूदा हेल्थ कवर और राइडर की शर्तें देखें। यह किसी विशेष प्लान की सिफारिश नहीं है।"
        if language == "te":
            return f"క్రిటికల్ ఇల్నెస్ ప్రయోజనం టర్మ్ ఇన్సూరెన్స్‌కు భిన్నం: కవర్ చేసిన వ్యాధి నిర్ధారణ తర్వాత నిబంధనలు, మినహాయింపులకు లోబడి ఒకేసారి మొత్తం చెల్లించవచ్చు. మీ వార్షిక కుటుంబ ఆదాయం ₹{analysis.annual_household_income:,.0f}, అత్యవసర పొదుపు ₹{profile.emergency_savings:,.0f}, అత్యవసర నిధి లోటు ₹{analysis.emergency_gap:,.0f}. నిర్ణయానికి ముందు ఉద్యోగ ప్రయోజనాలు, కుటుంబ వైద్య చరిత్ర, ప్రస్తుత హెల్త్ కవర్, రైడర్ నిబంధనలు పరిశీలించండి. ఇది ఏ ప్రత్యేక ప్లాన్ సిఫార్సు కాదు."
        if language == "ta":
            return f"கிரிட்டிக்கல் இல்னஸ் நன்மை டெர்ம் காப்பீட்டிலிருந்து வேறுபட்டது: கவர் செய்யப்பட்ட நோய் கண்டறியப்பட்டால் விதிகள் மற்றும் விலக்குகளுக்கு உட்பட்டு ஒருமுறை தொகை கிடைக்கலாம். உங்கள் ஆண்டு குடும்ப வருமானம் ₹{analysis.annual_household_income:,.0f}, அவசர சேமிப்பு ₹{profile.emergency_savings:,.0f}, அவசர நிதி பற்றாக்குறை ₹{analysis.emergency_gap:,.0f}. முடிவு செய்வதற்கு முன் வேலைவாய்ப்பு நன்மைகள், குடும்ப மருத்துவ வரலாறு, தற்போதைய ஹெல்த் கவர் மற்றும் ரைடர் விதிகளைப் பார்க்கவும். இது குறிப்பிட்ட திட்ட பரிந்துரை அல்ல."
        return (
            "A critical-illness benefit is different from term insurance: it usually pays a lump sum after a covered diagnosis, subject to definitions, survival periods and exclusions. "
            f"Your profile currently shows annual household income of ₹{analysis.annual_household_income:,.0f}, liquid emergency savings of ₹{profile.emergency_savings:,.0f}, and an emergency-fund gap of ₹{analysis.emergency_gap:,.0f}. "
            "Those figures help judge whether a temporary income shock could be absorbed, but they are not enough to decide on a rider by themselves. Consider employer benefits, family medical history, existing health cover, rider cost and the exact covered-condition definitions. This is a general explanation and does not recommend any particular plan."
        )
    if is_term:
        if language == "hi":
            return f"टर्म इंश्योरेंस कमाने वाले सदस्य की मृत्यु पर परिवार की आय और बड़े कर्ज की सुरक्षा के लिए है; यह निवेश उत्पाद नहीं है। आपके प्रोफ़ाइल में {profile.dependents} वित्तीय आश्रित, सालाना संयुक्त आय ₹{analysis.annual_household_income:,.0f}, देनदारियाँ ₹{analysis.total_liabilities:,.0f}, और अनुमानित अतिरिक्त टर्म कवर की कमी ₹{analysis.term_gap_crore:.2f} Cr है। यह किसी विशेष बीमाकर्ता या प्लान की सिफारिश नहीं है।"
        if language == "te":
            return f"సంపాదించే కుటుంబ సభ్యుడు మరణించినప్పుడు ఆదాయాన్ని భర్తీ చేసి పెద్ద అప్పులను తీర్చడానికి టర్మ్ ఇన్సూరెన్స్ ఉపయోగపడుతుంది; ఇది పెట్టుబడి ఉత్పత్తి కాదు. మీ ప్రొఫైల్‌లో {profile.dependents} ఆర్థిక ఆధారితులు, వార్షిక సంయుక్త ఆదాయం ₹{analysis.annual_household_income:,.0f}, బాధ్యతలు ₹{analysis.total_liabilities:,.0f}, అంచనా అదనపు టర్మ్ కవర్ లోటు ₹{analysis.term_gap_crore:.2f} Cr. ఇది ఏ ప్రత్యేక బీమా సంస్థ లేదా ప్లాన్ సిఫార్సు కాదు."
        if language == "ta":
            return f"வருமானம் ஈட்டும் குடும்ப உறுப்பினர் இறந்தால் வருமானத்தை மாற்றி பெரிய கடன்களைத் தீர்க்க டெர்ம் காப்பீடு உதவும்; இது முதலீட்டு தயாரிப்பு அல்ல. உங்கள் விவரத்தில் {profile.dependents} நிதி சார்ந்தவர்கள், ஆண்டு கூட்டு வருமானம் ₹{analysis.annual_household_income:,.0f}, கடன்கள் ₹{analysis.total_liabilities:,.0f}, மதிப்பிடப்பட்ட கூடுதல் டெர்ம் கவர் இடைவெளி ₹{analysis.term_gap_crore:.2f} Cr. இது குறிப்பிட்ட காப்பீட்டாளர் அல்லது திட்ட பரிந்துரை அல்ல."
        dependent_text = "no listed financial dependents" if profile.dependents == 0 else f"{profile.dependents} listed financial dependent{'s' if profile.dependents != 1 else ''}"
        return (
            "Term insurance is meant to replace income and clear major liabilities if an earning family member dies; it is protection, not an investment product. "
            f"Your profile shows {dependent_text}, combined earned income of ₹{analysis.annual_household_income:,.0f} per year, and liabilities of ₹{analysis.total_liabilities:,.0f}. "
            f"Using SurakshaCFO’s transparent rule—15× combined earned income plus liabilities, less existing term cover—your estimated additional term-cover gap is ₹{analysis.term_gap_crore:.2f} Cr. "
            "That gap is why term insurance may matter for your family. The exact amount and tenure should still reflect how long dependents need support, loan duration, education goals, existing assets and affordability. This explanation does not recommend any particular insurer or plan."
        )
    if is_health:
        if language == "hi":
            return f"हेल्थ इंश्योरेंस बड़ी चिकित्सा लागत से बचत और नकदी प्रवाह की रक्षा करता है। आपका प्रोफ़ाइल-आधारित फैमिली फ्लोटर लक्ष्य ₹{analysis.recommended_health_cover_lakh:.1f} लाख और वर्तमान अनुमानित कमी ₹{analysis.health_gap_lakh:.1f} लाख है। किसी नामित प्लान के बारे में पूछने पर ही वेटिंग पीरियड, अपवाद, को-पे और रूम लिमिट की तुलना करें।"
        if language == "te":
            return f"హెల్త్ ఇన్సూరెన్స్ పెద్ద వైద్య ఖర్చుల నుండి పొదుపు, నగదు ప్రవాహాన్ని రక్షిస్తుంది. మీ ప్రొఫైల్ ఆధారిత ఫ్యామిలీ ఫ్లోటర్ లక్ష్యం ₹{analysis.recommended_health_cover_lakh:.1f} లక్షలు, ప్రస్తుత అంచనా లోటు ₹{analysis.health_gap_lakh:.1f} లక్షలు. పేరు చెప్పిన ప్లాన్ గురించి అడిగినప్పుడు మాత్రమే వెయిటింగ్ పీరియడ్, మినహాయింపులు, కో-పే, రూమ్ లిమిట్‌లను పోల్చండి."
        if language == "ta":
            return f"ஹெல்த் காப்பீடு பெரிய மருத்துவ செலவுகளிலிருந்து சேமிப்பு மற்றும் பணப்புழக்கத்தை பாதுகாக்கிறது. உங்கள் விவர அடிப்படையிலான ஃபேமிலி ஃப்ளோட்டர் இலக்கு ₹{analysis.recommended_health_cover_lakh:.1f} லட்சம்; தற்போதைய மதிப்பிடப்பட்ட இடைவெளி ₹{analysis.health_gap_lakh:.1f} லட்சம். பெயரிட்ட திட்டம் பற்றி கேட்டால் மட்டுமே காத்திருப்பு காலம், விலக்குகள், கோ-பே, அறை வரம்புகளை ஒப்பிடவும்."
        return (
            "Health insurance protects savings and cashflow from large medical bills; it should be evaluated separately from term insurance. "
            f"Your profile-based floater target is ₹{analysis.recommended_health_cover_lakh:.1f} lakh and the estimated current gap is ₹{analysis.health_gap_lakh:.1f} lakh. "
            "Compare waiting periods, exclusions, co-pay, room-rent limits and restoration only when you ask about named plans."
        )
    if language == "hi":
        return f"आपके वित्तीय प्रोफ़ाइल के आधार पर सुरक्षा स्कोर {analysis.protection_score}/100, टर्म कवर की कमी ₹{analysis.term_gap_crore:.2f} Cr, हेल्थ कवर की कमी ₹{analysis.health_gap_lakh:.1f} लाख, और आपात रिज़र्व लगभग {analysis.emergency_months:.1f} महीने का है।"
    if language == "te":
        return f"మీ ఆర్థిక ప్రొఫైల్ ఆధారంగా రక్షణ స్కోర్ {analysis.protection_score}/100, టర్మ్ కవర్ లోటు ₹{analysis.term_gap_crore:.2f} Cr, హెల్త్ కవర్ లోటు ₹{analysis.health_gap_lakh:.1f} లక్షలు, అత్యవసర నిధి సుమారు {analysis.emergency_months:.1f} నెలలు."
    if language == "ta":
        return f"உங்கள் நிதி விவரத்தின் அடிப்படையில் பாதுகாப்பு மதிப்பெண் {analysis.protection_score}/100, டெர்ம் கவர் இடைவெளி ₹{analysis.term_gap_crore:.2f} Cr, ஹெல்த் கவர் இடைவெளி ₹{analysis.health_gap_lakh:.1f} லட்சம், அவசர நிதி சுமார் {analysis.emergency_months:.1f} மாதங்கள்."
    return (
        f"Based only on your financial profile, your protection score is {analysis.protection_score}/100, your estimated term gap is ₹{analysis.term_gap_crore:.2f} Cr, "
        f"your health-cover gap is ₹{analysis.health_gap_lakh:.1f} lakh, and your emergency reserve covers about {analysis.emergency_months:.1f} months. "
        "Ask a general protection question for a profile-based explanation, or name a plan/provider when you want document-grounded plan details."
    )


def _profile_context(profile: ProfileInput | None) -> str:
    if not profile:
        return "User has not completed a profile."
    analysis = _analysis(profile)
    return (
        f"User profile: {profile.dependents} financial dependents, annual household income ₹{analysis.annual_household_income:,.0f}, "
        f"liabilities ₹{analysis.total_liabilities:,.0f}, emergency reserve {analysis.emergency_months:.1f} months, "
        f"term-cover gap ₹{analysis.term_gap_crore:.2f} Cr, recommended health cover ₹{analysis.recommended_health_cover_lakh:.1f} lakh "
        f"(gap ₹{analysis.health_gap_lakh:.1f} lakh), protection score {analysis.protection_score}/100."
    )


def _open_system_message(language_name: str, profile_context: str, conversation: str, source_context: str) -> str:
    return (
        "You are SurakshaCFO's friendly personal-finance and insurance advisor for an Indian family. Answer every in-scope question the user asks, "
        "whether it is general finance or insurance knowledge or about specific plans. Be direct and concise, and give a clear recommendation "
        "when asked which option to take, with reasons tied to the user's profile.\n"
        f"{SCOPE_RULES}\n"
        "- Use the user's profile and the recent conversation to personalise the answer and to resolve follow-ups such as 'which should I take'.\n"
        "- INDEXED PLAN DOCUMENTS below are the plans on this platform. For questions about choosing, comparing or coverage of plans, use them: "
        "name each plan by its exact title and state only facts found in the excerpts. If the excerpts do not state something (premium, waiting period, exclusions), say so. "
        "Ignore excerpts that are not relevant to the question.\n"
        "- Use general knowledge for concepts (term vs health cover, riders, waiting periods, how much cover is enough) and label it as general. "
        "Never invent plan-specific facts, premiums, claim ratios, tax advice or guarantees.\n"
        "- This is educational guidance, not licensed advice; remind the user to verify the current policy schedule before buying.\n"
        f"Write the entire answer in {language_name}. Keep insurer names, plan names, monetary values and legal terms exactly as written in the source.\n\n"
        f"{profile_context}\n\n"
        f"RECENT CONVERSATION:\n{conversation or '(none)'}\n\n"
        f"INDEXED PLAN DOCUMENTS:\n{source_context or 'No indexed plan document matched this question.'}"
    )


def _comparison_fallback(sources: list[dict], language: str) -> str:
    grouped: dict[str, str] = {}
    for source in sources:
        grouped.setdefault(source["document_title"], source["text"][:240].replace("|", "/"))
    titles = list(grouped)
    labels = {
        "hi": ("विशेषता", "इंडेक्स प्रमाण", "प्रीमियम", "पात्रता", "प्रोफ़ाइल उपयुक्तता", "इंडेक्स दस्तावेज़ में नहीं बताया गया", "सलाहकार समीक्षा आवश्यक"),
        "te": ("లక్షణం", "ఇండెక్స్ ఆధారం", "ప్రీమియం", "అర్హత", "ప్రొఫైల్ సరిపోలిక", "ఇండెక్స్ పత్రాల్లో పేర్కొనలేదు", "సలహాదారు సమీక్ష అవసరం"),
        "ta": ("அம்சம்", "அட்டவணை ஆதாரம்", "பிரீமியம்", "தகுதி", "விவர பொருத்தம்", "அட்டவணை ஆவணங்களில் குறிப்பிடப்படவில்லை", "ஆலோசகர் மதிப்பாய்வு தேவை"),
    }.get(language, ("Feature", "Indexed evidence", "Premium", "Eligibility", "Profile fit", "Not stated in indexed documents", "Requires advisor review"))
    header = f"| {labels[0]} | " + " | ".join(titles) + " |"
    divider = "| --- | " + " | ".join("---" for _ in titles) + " |"
    evidence = f"| {labels[1]} | " + " | ".join(grouped[title] for title in titles) + " |"
    missing_rows = [
        f"| {labels[2]} | " + " | ".join(labels[5] for _ in titles) + " |",
        f"| {labels[3]} | " + " | ".join(labels[5] for _ in titles) + " |",
        f"| {labels[4]} | " + " | ".join(labels[6] for _ in titles) + " |",
    ]
    return "\n".join([header, divider, evidence, *missing_rows, "", "This comparison includes only retrieved evidence. Verify the current policy schedules before deciding."])


@router.get("/history", response_model=list[ChatMessageRecord])
async def chat_history(user: dict = Depends(get_current_user)) -> list[ChatMessageRecord]:
    messages = await db.chat_messages.find({"user_id": user["id"]}, {"_id": 0, "user_id": 0}).sort("created_at", 1).to_list(100)
    return [ChatMessageRecord(**message) for message in messages]


@router.post("/stream")
async def stream_chat(question: ChatQuestion, user: dict = Depends(get_current_user)) -> StreamingResponse:
    profile_doc = await db.profiles.find_one({"_id": user["id"]})
    profile = ProfileInput(**profile_doc["profile"]) if profile_doc else None
    language = user.get("preferred_language", "en")
    language_name = LANGUAGE_NAMES.get(language, "English")
    lower_question = f" {question.question.lower()} "
    is_comparison = any(word in lower_question for word in COMPARISON_WORDS)
    active_documents = await db.rag_documents.find({"enabled": {"$ne": False}}, {"_id": 0, "id": 1, "title": 1}).to_list(500)
    matched_document_ids = _matching_document_ids(question.question, active_documents)
    is_plan_specific = bool(matched_document_ids)
    use_documents = is_comparison or is_plan_specific
    # With an LLM configured, a question that names no plan is still answered: the model sees the profile, the recent
    # conversation and the best chunks of every relevant plan, and decides what is relevant. Without one, the gated
    # deterministic behaviour below is kept.
    open_mode = llm_configured() and not use_documents
    recent = await db.chat_messages.find({"user_id": user["id"]}, {"_id": 0, "role": 1, "text": 1}).sort("created_at", -1).to_list(HISTORY_LIMIT)
    history = list(reversed(recent))
    if open_mode:
        sources = await retrieve_across_documents(build_retrieval_query(question.question, history))
    else:
        sources = await retrieve(question.question, document_ids=matched_document_ids) if matched_document_ids else []
    source_context = "\n\n".join(f"SOURCE: {item['document_title']}\n{item['text']}" for item in sources)
    profile_context = _profile_context(profile)
    profile_source = {"hi": "आपका वित्तीय प्रोफ़ाइल", "te": "మీ ఆర్థిక ప్రొఫైల్", "ta": "உங்கள் நிதி விவரம்"}.get(language, "Your financial profile")

    async def generator() -> AsyncIterator[str]:
        await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "you", "text": question.question, "sources": [], "created_at": datetime.now(timezone.utc)})
        source_titles = list(dict.fromkeys(item["document_title"] for item in sources))
        if open_mode:
            system_message = _open_system_message(language_name, profile_context, format_history(history), source_context)
            try:
                answer = ""
                async for delta in stream_answer(system_message, question.question):
                    answer += delta
                    yield _event({"type": "delta", "content": delta})
                cited = cited_titles(answer, [item["document_title"] for item in sources]) or [profile_source]
                done: dict = {"type": "done", "sources": cited}
            except Exception:
                answer = _general_profile_answer(question.question, profile, language)
                yield _event({"type": "delta", "content": answer})
                cited = [profile_source]
                done = {"type": "done", "sources": cited, "mode": "general", "fallback": True}
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": cited, "created_at": datetime.now(timezone.utc)})
            yield _event(done)
            return
        if not use_documents:
            answer = _general_profile_answer(question.question, profile, language)
            yield _event({"type": "delta", "content": answer})
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": [profile_source], "created_at": datetime.now(timezone.utc)})
            yield _event({"type": "done", "sources": [profile_source], "mode": "general"})
            return
        if not sources:
            answer = {
                "hi": "इस अनुरोध के प्लान के लिए सक्रिय इंडेक्स दस्तावेज़ नहीं मिले। तुलना से पहले एडमिन से सही दस्तावेज़ जोड़ने या सक्रिय करने को कहें; मैं किसी असंबंधित पॉलिसी का उपयोग नहीं करूँगा।",
                "te": "ఈ అభ్యర్థనలోని ప్లాన్‌లకు సక్రియ ఇండెక్స్ పత్రాలు దొరకలేదు. పోలికకు ముందు సరైన పత్రాలను జోడించమని లేదా సక్రియం చేయమని అడ్మిన్‌ను కోరండి; సంబంధం లేని పాలసీని ఉపయోగించను.",
                "ta": "இந்த கோரிக்கையில் உள்ள திட்டங்களுக்கு செயலில் உள்ள ஆவணங்கள் கிடைக்கவில்லை. ஒப்பிடுவதற்கு முன் சரியான ஆவணங்களை சேர்க்க அல்லது செயல்படுத்த நிர்வாகியை கேட்கவும்; தொடர்பில்லாத பாலிசியைப் பயன்படுத்த மாட்டேன்.",
            }.get(language, "I could not find active indexed documents for the plans in that request. Ask an admin to add or activate those documents; I will not substitute an unrelated policy.")
            yield _event({"type": "delta", "content": answer})
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": [], "created_at": datetime.now(timezone.utc)})
            yield _event({"type": "done", "sources": []})
            return
        if not llm_configured():
            answer = _comparison_fallback(sources, language) if is_comparison else _fallback(question.question, profile, sources, language)
            yield _event({"type": "delta", "content": answer})
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": source_titles, "created_at": datetime.now(timezone.utc)})
            yield _event({"type": "done", "sources": source_titles})
            return
        system_message = (
            "You are SurakshaCFO's insurance document advisor. Answer only from the indexed insurance excerpts below and the user's profile context. "
            "If the excerpts do not answer the question, say that the documents do not establish it. Never invent coverage, claim ratios, premiums, tax advice, or guarantees. "
            "Explain exclusions and uncertainty clearly, and remind the user to verify the current policy schedule. "
            + f"Write the entire answer in {language_name}. Keep insurer names, plan names, source titles, monetary values, percentages, clause identifiers and legal terms exactly as written in the source when translating could change their meaning. "
            + ("The user explicitly requested a comparison. Start with a Markdown table. Use one row per feature and one column per named plan. Include policy type, eligibility, cover, premium, waiting periods, exclusions, riders, claim/payment terms, co-pay or room limits where relevant, and profile fit. Write 'Not stated in indexed documents' for missing facts. After the table, give a neutral evidence-based summary; do not select a winner unless the documents establish it. " if is_comparison else "Discuss only the plan or provider explicitly named by the user. ")
            + "\n\n"
            + f"{profile_context}\n\nRECENT CONVERSATION:\n{format_history(history) or '(none)'}\n\nINDEXED DOCUMENTS:\n{source_context}"
        )
        try:
            answer = ""
            async for delta in stream_answer(system_message, question.question):
                answer += delta
                yield _event({"type": "delta", "content": delta})
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": source_titles, "created_at": datetime.now(timezone.utc)})
            yield _event({"type": "done", "sources": source_titles})
        except Exception:
            answer = _comparison_fallback(sources, language) if is_comparison else _fallback(question.question, profile, sources, language)
            yield _event({"type": "delta", "content": answer})
            await db.chat_messages.insert_one({"_id": str(uuid.uuid4()), "id": str(uuid.uuid4()), "user_id": user["id"], "role": "advisor", "text": answer, "sources": source_titles, "created_at": datetime.now(timezone.utc)})
            yield _event({"type": "done", "sources": source_titles, "fallback": True})

    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})