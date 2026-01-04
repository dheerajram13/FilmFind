export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <main className="flex flex-col items-center gap-8">
        <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          FilmFind
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 text-center max-w-2xl">
          Discover movies using natural language and AI-powered semantic search
        </p>
        <div className="text-sm text-gray-500">
          Next.js 14 + TypeScript + TailwindCSS
        </div>
      </main>
    </div>
  );
}
