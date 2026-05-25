export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <main className="flex flex-col items-center gap-6 text-center px-6">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Novestia
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          Learn investing with real market data, paper trading, and AI-powered
          insights. No real money. No risk.
        </p>
      </main>
    </div>
  );
}
