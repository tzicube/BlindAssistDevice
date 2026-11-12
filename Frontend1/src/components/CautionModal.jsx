import { useEffect } from "react";
import {
  LuActivity,
  LuClock3,
  LuNavigation2,
  LuTriangleAlert,
  LuX,
} from "react-icons/lu";

function formatNumber(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "—";
}

function formatEventTime(value) {
  const timestamp = Number(value);
  if (!Number.isFinite(timestamp)) return "—";
  const eventDate = new Date(timestamp);
  if (Number.isNaN(eventDate.getTime())) return "—";
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(eventDate);
}

export default function CautionModal({ caution, onClose }) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  if (!caution) return null;

  const isFall = caution.event === "fall";
  const heading = Number(caution.heading);
  const direction = caution.direction || "—";

  return (
    <div className="fixed inset-0 z-[1000] grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <section
        className="w-full max-w-xl overflow-hidden rounded-3xl border border-red-300 bg-white shadow-2xl shadow-red-950/30"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="caution-title"
        aria-describedby="caution-message"
      >
        <div className="relative bg-red-600 px-6 py-6 text-white sm:px-8">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full bg-white/15 transition hover:bg-white/25 focus:outline-none focus:ring-2 focus:ring-white"
            aria-label="關閉警報"
          >
            <LuX className="h-5 w-5" aria-hidden="true" />
          </button>
          <div className="flex items-center gap-4 pr-12">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-white/15">
              <LuTriangleAlert className="h-8 w-8" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold tracking-[0.2em] text-red-100">
                緊急安全通知
              </p>
              <h2 id="caution-title" className="mt-1 text-3xl font-bold">
                危險警報
              </h2>
            </div>
          </div>
        </div>

        <div className="space-y-5 p-6 sm:p-8">
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
            <p className="text-sm font-bold text-red-700">
              {isFall ? "偵測到疑似跌倒" : "偵測到危險事件"}
            </p>
            <p id="caution-message" className="mt-2 text-xl font-semibold text-slate-950">
              {caution.message || "使用者可能需要立即協助"}
            </p>
            <p className="mt-2 text-sm text-red-700">
              請立即確認使用者目前的安全狀況
            </p>
          </div>

          <dl className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <LuActivity className="h-4 w-4 text-red-600" aria-hidden="true" />
                重力數值
              </dt>
              <dd className="mt-2 text-lg font-semibold text-slate-900">
                {formatNumber(caution.sizeG)} G
              </dd>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <LuNavigation2 className="h-4 w-4 text-red-600" aria-hidden="true" />
                面向方向
              </dt>
              <dd className="mt-2 text-lg font-semibold text-slate-900">
                {direction}
                {Number.isFinite(heading) ? ` · ${heading.toFixed(0)}°` : ""}
              </dd>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:col-span-2">
              <dt className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <LuClock3 className="h-4 w-4 text-red-600" aria-hidden="true" />
                事件時間
              </dt>
              <dd className="mt-2 font-semibold text-slate-900">
                {formatEventTime(caution.time)}
              </dd>
              <dd className="mt-1 text-xs text-slate-500">
                來源 {caution.source || "—"} · 感測器 {caution.sensor || "—"}
              </dd>
            </div>
          </dl>

          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-2xl bg-red-600 px-5 py-3.5 text-base font-bold text-white shadow-lg shadow-red-200 transition hover:bg-red-700 focus:outline-none focus:ring-4 focus:ring-red-200"
          >
            已收到並關閉警報
          </button>
        </div>
      </section>
    </div>
  );
}
