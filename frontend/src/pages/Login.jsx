import { useState } from "react";
import API from "../api/axios";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [form, setForm] = useState({
    username: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const params = new URLSearchParams();
      params.append("username", form.username);
      params.append("password", form.password);

      const res = await API.post(
        "/api/auth/login",
        params,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      // store JWT token
      localStorage.setItem("token", res.data.access_token);

      // redirect to dashboard
      navigate("/dashboard");
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail ||
        JSON.stringify(err.response?.data) ||
        "Login failed";

      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex items-center justify-center">
      <form onSubmit={handleLogin} className="card w-96">
        <h2 className="text-2xl mb-6 text-center">Login</h2>

        <input
          name="username"
          required
          className="input"
          placeholder="Username"
          value={form.username}
          onChange={(e) =>
            setForm({ ...form, username: e.target.value })
          }
        />

        <input
          name="password"
          type="password"
          required
          className="input"
          placeholder="Password"
          value={form.password}
          onChange={(e) =>
            setForm({ ...form, password: e.target.value })
          }
        />

        <button
          type="submit"
          className="btn-primary"
          disabled={loading}
        >
          {loading ? "Logging in..." : "Login"}
        </button>

        <p
          className="text-center mt-4 text-gray-400 cursor-pointer hover:text-white transition"
          onClick={() => navigate("/signup")}
        >
          Create account
        </p>
      </form>
    </div>
  );
}