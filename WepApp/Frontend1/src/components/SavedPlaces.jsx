export default function SavedPlaces({
  places,
  onDelete,
}) {
  return (
    <div className="bg-white rounded shadow p-4 h-full">

      <h2 className="font-bold text-xl mb-4">
        Saved Places
      </h2>

      {places.length === 0 && (
        <p className="text-gray-500 text-center py-4">
          No saved places
        </p>
      )}

      {places.map((place) => (
        <div
          key={place.id}
          className="border-b py-3"
        >
          <div className="flex items-start justify-between gap-2">

            <div>
              <h3 className="font-semibold">
                {place.name}
              </h3>

              <p className="text-gray-500 text-sm">
                Latitude:{" "}
                {Number(place.lat).toFixed(6)}
              </p>

              <p className="text-gray-500 text-sm">
                Longitude:{" "}
                {Number(place.lng).toFixed(6)}
              </p>
            </div>

            <button
              onClick={() =>
                onDelete(place.id)
              }
              className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
            >
              Delete
            </button>

          </div>
        </div>
      ))}

      <button
        className="bg-blue-500 text-white w-full mt-4 p-3 rounded disabled:opacity-50"
        disabled={places.length === 0}
      >
        Start Navigation
      </button>

    </div>
  );
}