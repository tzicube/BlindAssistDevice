export default function MapPanel({
  navigation,
}) {
  return (
    <div className="bg-white rounded shadow p-4 h-full">

      <h2 className="font-bold text-xl mb-4">
        Live Location
      </h2>

      <div className="bg-gray-200 h-96 rounded flex items-center justify-center">

        Map Area

      </div>

      <div className="grid grid-cols-3 gap-4 mt-4">

        <div>
          <p className="text-gray-500">
            Distance
          </p>

          <h3 className="font-bold">
            {navigation.distance}
          </h3>
        </div>

        <div>
          <p className="text-gray-500">
            ETA
          </p>

          <h3 className="font-bold">
            {navigation.eta}
          </h3>
        </div>

        <div>
          <p className="text-gray-500">
            Next
          </p>

          <h3 className="font-bold">
            {navigation.nextInstruction}
          </h3>
        </div>

      </div>
    </div>
  );
}