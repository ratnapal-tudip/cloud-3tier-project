import { useState } from "react";
import API from "../api/axios";
import { useNavigate } from "react-router-dom";

export default function Signup() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    full_name: "",
  });

  const handleSignup = async (e) => {
    e.preventDefault();
    try {
      await API.post("/api/auth/signup", form);
      alert("User created!");
      navigate("/");
    } catch (err) {
      alert(err.response?.data?.detail || "Signup failed");
    }
  };

  return (
    <div className="h-screen flex items-center justify-center">
      <form onSubmit={handleSignup} className="card w-96">
        <h2 className="text-2xl mb-6 text-center">Signup</h2>

        <input className="input" placeholder="Username"
          onChange={(e)=>setForm({...form, username:e.target.value})} />

        <input className="input" placeholder="Email"
          onChange={(e)=>setForm({...form, email:e.target.value})} />

        <input type="password" className="input" placeholder="Password"
          onChange={(e)=>setForm({...form, password:e.target.value})} />

        <input className="input" placeholder="Full Name"
          onChange={(e)=>setForm({...form, full_name:e.target.value})} />

        <button className="btn-primary">Create Account</button>
      </form>
    </div>
  );
}