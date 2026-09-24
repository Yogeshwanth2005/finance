import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import Insurance from "@/pages/Insurance";
import Investments from "@/pages/Investments";
import Login from "@/pages/Login";
import ResetPassword from "@/pages/ResetPassword";
import AdminDocuments from "@/pages/AdminDocuments";
import Account from "@/pages/Account";
import { AdminRoute, ProtectedRoute } from "@/components/ProtectedRoute";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/investments" element={<Investments />} />
        <Route path="/insurance" element={<Insurance />} />
        <Route path="/account" element={<Account />} />
        <Route element={<AdminRoute />}>
          <Route path="/admin/documents" element={<AdminDocuments />} />
        </Route>
      </Route>
    </Routes>
  );
}
