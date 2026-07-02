export default function SavedPlaces({
  places,
}) {
  return (
    <div className="bg-white rounded shadow p-4 h-full">

      <h2 className="font-bold text-xl mb-4">
        Saved Places
      </h2>

      {places.map((place) => (
        <div
          key={place.id}
          className="border-b py-3"
        >
          <h3 className="font-semibold">
            {place.name}
          </h3>

          <p className="text-gray-500">
            {place.address}
          </p>
        </div>
      ))}

      <button className="bg-blue-500 text-white w-full mt-4 p-3 rounded">

        Start Navigation

      </button>

    </div>
  );
}