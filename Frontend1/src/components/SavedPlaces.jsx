import { LuBookmark, LuMapPin, LuTrash2 } from "react-icons/lu";

function formatCoordinate(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(5) : "—";
}

export default function SavedPlaces({ places, onDelete }) {
  return (
    <section
      className="panel-card flex h-full min-h-0 flex-col overflow-hidden"
      aria-labelledby="places-title"
    >
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6 2xl:px-7 2xl:py-5">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-violet-50 text-violet-700">
            <LuBookmark className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="places-title" className="text-lg font-semibold text-slate-950">
              Saved places
            </h2>
            <p className="text-sm text-slate-500">Locations ready for later use</p>
          </div>
        </div>
        <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">
          {places.length}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5 2xl:p-7">
        {places.length === 0 ? (
          <div className="grid min-h-36 place-items-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center">
            <div>
              <LuMapPin className="mx-auto h-6 w-6 text-slate-400" aria-hidden="true" />
              <p className="mt-3 font-medium text-slate-700">No saved places yet</p>
              <p className="mt-1 text-sm text-slate-500">
                Click anywhere on the map to add one.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid gap-3">
            {places.map((place) => (
              <article
                key={place.id}
                className="group flex min-w-0 items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md hover:shadow-slate-200/60"
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-600">
                  <LuMapPin className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate font-semibold text-slate-900">{place.name}</h3>
                  {place.address && (
                    <p className="mt-1 line-clamp-2 text-sm leading-5 text-slate-600">
                      {place.address}
                    </p>
                  )}
                  <p className="mt-1 truncate font-mono text-xs text-slate-500">
                    {formatCoordinate(place.lat)}, {formatCoordinate(place.lng)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onDelete(place.id)}
                  className="icon-button shrink-0 text-slate-400 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"
                  aria-label={`Delete ${place.name}`}
                  title={`Delete ${place.name}`}
                >
                  <LuTrash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
