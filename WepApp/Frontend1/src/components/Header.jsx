export default function Header({
  battery,
  online,
  gps,
  signal,
  time,
}) {
  return (
    <header className="bg-slate-900 text-white p-4 flex justify-between items-center">
      <div>
        <h1 className="text-2xl font-bold">
          Blind Navigation Support Dashboard
        </h1>

        <p className="text-gray-300">
          AI Powered Navigation System
        </p>
      </div>

      <div className="flex gap-3 items-center">

        <div className="border px-3 py-2 rounded">
          {online ? "🟢 Online" : "🔴 Offline"}
        </div>

        <div className="border px-3 py-2 rounded">
          🔋 {battery}%
        </div>

        <div className="border px-3 py-2 rounded">
          📡 {signal}
        </div>

        <div className="border px-3 py-2 rounded">
          📍 {gps}
        </div>

        <div className="border px-3 py-2 rounded">
          🕒 {time}
        </div>

        <button className="bg-red-500 px-6 py-2 rounded">
          SOS
        </button>

      </div>
    </header>
  );
}