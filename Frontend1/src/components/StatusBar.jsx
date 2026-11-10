export default function StatusBar() {
  return (
    <div
      id="status-bar"
      className="status-bar bg-white shadow mt-4 p-4 grid grid-cols-4"
    >
      <div className="status-card" id="status-last-update">
        Last Update
      </div>

      <div className="status-card" id="status-signal">
        Signal 
      </div>

      <div className="status-card" id="status-navigation">
        Navigating
      </div>

      <div className="status-card" id="status-system">
        System Status
      </div>
    </div>
  );
}