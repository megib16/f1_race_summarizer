export default function Home() {
  return (
    <div className="bg-gray-900 text-white p-8">
      <h1 className="text-5xl font-bold text-red-600 text-center font-[family-name:--font-orbitron]">Australian Grand Prix 2026</h1>
      <p className="text-2xl text-gray-400 mt-2">Melbourne 08.03.2026 - 71 Laps</p>

      {/* Podium */}
      <div className="flex justify-center items-end gap-4 mt-8">

        {/* P2 */}
        <div className="bg-gray-800 p-6 rounded-lg text-center w-48">
          <p className="text-gray-400 text-sm">2nd Place</p>
          <p className="text-xl font-bold mt-1">Driver Name</p>
          <p className="text-gray-400">Team</p>
        </div>

        {/* P1 - bigger */}
        <div className="bg-red-900 p-8 rounded-lg text-center w-56">
          <p className="text-yellow-400 text-sm font-bold">RACE WINNER</p>
          <p className="text-2xl font-bold mt-1">Driver Name</p>
          <p className="text-gray-400">Team</p>
        </div>

        {/* P3 */}
        <div className="bg-gray-800 p-6 rounded-lg text-center w-48">
          <p className="text-gray-400 text-sm">3rd Place</p>
          <p className="text-xl font-bold mt-1">Driver Name</p>
          <p className="text-gray-400">Team</p>
        </div>

      </div>
    </div>
  )
}