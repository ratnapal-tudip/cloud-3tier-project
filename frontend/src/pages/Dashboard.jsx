import { useEffect, useState } from "react";
import API from "../api/axios";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token"); // remove JWT
    navigate("/"); // go back to login
  };

  useEffect(() => {
    API.get("/api/dashboard")
      .then((res) => setData(res.data))
      .catch(() => {
        localStorage.removeItem("token");
        navigate("/");
      });
  }, [navigate]);

  if (!data) return <div className="p-10">Loading...</div>;

  return (
    <div className="p-10">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl">{data.message}</h1>

        <button
          onClick={handleLogout}
          className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
        >
          Logout
        </button>
      </div>

      {/* Dashboard cards */}
      <div className="grid grid-cols-3 gap-6">
        <div className="card">
          <h2>Projects</h2>
          <p>{data.dashboard_data.total_projects}</p>
        </div>

        <div className="card">
          <h2>Activity</h2>
          <p>{data.dashboard_data.recent_activity}</p>
        </div>

        <div className="card">
          <h2>Status</h2>
          <p>{data.dashboard_data.server_status}</p>
        </div>
      </div>
    </div>
  );
}