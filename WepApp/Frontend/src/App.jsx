import { useState } from "react";
import Header from "./components/Header";
import Home from "./pages/Home";
import EditHouse from "./pages/EditHouse";
import "./styles/App.css";
import GridEditor from "./components/GridEditor";
function App() {
  const [page, setPage] = useState("home");

  return (
    <div className="app-shell">
      <div className="app-background" />

      <div className="app">
        <Header page={page} setPage={setPage} />

        <main className="page-content">
          {page === "home" ? <Home /> : <EditHouse />}
        </main>
      </div>
    </div>
  );
}

export default App;
