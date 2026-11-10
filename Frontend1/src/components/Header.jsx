import {
  LuAccessibility,
  LuBattery,
  LuBatteryLow,
  LuClock3,
  LuMapPin,
  LuNavigation2,
  LuServer,
  LuWifi,
  LuWifiOff,
} from "react-icons/lu";

export default function Header({
  online,
  backendOnline,
  battery,
  address,
  heading,
  direction,
  gps,
  time,
}) {
  const connection = online
    ? {
        label: "Device data live",
        detail: "Receiving location",
        dot: "bg-emerald-500",
        icon: LuWifi,
      }
    : backendOnline
      ? {
          label: "Backend connected",
          detail: "Waiting for device",
          dot: "bg-amber-400",
          icon: LuServer,
        }
      : {
          label: "Services offline",
          detail: "Check the backend",
          dot: "bg-rose-500",
          icon: LuWifiOff,
        };

  const ConnectionIcon = connection.icon;
  const parsedBattery = Number(battery);
  const batteryPercent = Number.isFinite(parsedBattery)
    ? Math.max(0, Math.min(100, Math.round(parsedBattery)))
    : null;
  const BatteryIcon = batteryPercent !== null && batteryPercent <= 20
    ? LuBatteryLow
    : LuBattery;
  const batteryTone = batteryPercent === null
    ? "text-slate-400"
    : batteryPercent <= 20
      ? "text-rose-600"
      : batteryPercent <= 40
        ? "text-amber-500"
        : "text-emerald-600";
  const headingNumber = heading === null || heading === undefined || heading === ""
    ? null
    : Number(heading);
  const headingDegrees = Number.isFinite(headingNumber)
    ? ((headingNumber % 360) + 360) % 360
    : null;
  const directionText = direction && headingDegrees !== null
    ? `${direction} · ${headingDegrees.toFixed(0)}°`
    : direction || "Waiting for heading";

  return (
    <header className="border-b border-slate-200/80 bg-white/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-none flex-col gap-4 px-3 py-4 sm:px-4 lg:flex-row lg:items-center lg:justify-between lg:px-5 2xl:px-6 2xl:py-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-blue-600 text-white shadow-sm shadow-blue-200">
            <LuAccessibility className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
              ClearPath
            </p>
            <h1 className="truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
              Navigation support
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-sm">
          <div className="flex items-center gap-2.5 rounded-2xl border border-slate-200 bg-slate-50 px-3.5 py-2.5">
            <span className={`h-2.5 w-2.5 rounded-full ${connection.dot}`} />
            <ConnectionIcon className="h-4 w-4 text-slate-500" aria-hidden="true" />
            <div className="leading-tight">
              <p className="font-medium text-slate-800">{connection.label}</p>
              <p className="text-xs text-slate-500">{connection.detail}</p>
            </div>
          </div>

          <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5 text-slate-600">
            <LuMapPin className="h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" />
            <span className="max-w-[260px] truncate" title={address || gps}>
              {address || gps || "Waiting for location"}
            </span>
          </div>

          <div className="flex items-center gap-2.5 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-slate-600">
            <span className="relative grid h-9 w-9 shrink-0 place-items-center rounded-full border border-indigo-100 bg-indigo-50">
              <span className="absolute top-0.5 text-[7px] font-bold leading-none text-indigo-400">N</span>
              <LuNavigation2
                className="h-5 w-5 text-indigo-600 transition-transform duration-500 ease-out"
                style={{ transform: `rotate(${headingDegrees ?? 0}deg)` }}
                aria-hidden="true"
              />
            </span>
            <div className="leading-tight">
              <p className="font-medium tabular-nums text-slate-700">{directionText}</p>
              <p className="text-[11px] text-slate-400">Device heading</p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5">
            <BatteryIcon className={`h-4 w-4 shrink-0 ${batteryTone}`} aria-hidden="true" />
            <span className={`font-semibold tabular-nums ${batteryTone}`}>
              {batteryPercent === null ? "--%" : `${batteryPercent}%`}
            </span>
          </div>

          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5 font-medium tabular-nums text-slate-700">
            <LuClock3 className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <time>{time || "--:--:--"}</time>
          </div>
        </div>
      </div>
    </header>
  );
}
