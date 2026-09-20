# SurakshaCFO auth and RAG testing playbook

## Demo admin
- Email: `admin@surakshacfo.demo`
- Password: `DemoAdmin!2026`
- Admin page: `/admin/documents`

## Core checks
1. Register a user at `/login`, confirm the browser lands on the profile wizard.
2. Complete the wizard, confirm `/dashboard` is personalized to the account.
3. Sign out, reload, and confirm protected pages redirect to `/login`.
4. Sign back in and confirm the profile/dashboard persist.
5. As admin, upload a PDF/TXT/DOCX or web URL and confirm an indexed document appears.
6. As a user, ask the chatbot a document-specific question and confirm streamed answer text plus source titles.
7. Use forgot password, follow the demo reset token, then log in with the new password.