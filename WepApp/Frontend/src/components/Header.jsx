import { useEffect, useState } from "react";

function Header({ page, setPage }) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();

      const formatted =
        now.toLocaleDateString() +
        " " +
        now.toLocaleTimeString();

      setTime(formatted);
    };

    updateTime();

    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <header className="header">
      <div className="header-left">
        <button
          className={page === "home" ? "active" : ""}
          onClick={() => setPage("home")}
        >
          <span>🏠</span>
          <p>Home</p>
        </button>

        <button>
          <span>❓</span>
          <p>Help</p>
        </button>
      </div>

      <div className="header-center">
        <h1>Indoor Navigation</h1>
        <p>{time}</p>
      </div>

      <button
        className="edit-house-btn"
        onClick={() => setPage("edit")}
      >
        ⚙ Chỉnh sửa nhà
      </button>
    </header>
  );
}

export default Header;