export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-elite opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-elite" />
          </span>
          <span className="text-base font-bold tracking-tight text-ink">
            Sharp<span className="text-accent">Edge</span>
          </span>
        </div>
        <p className="hidden text-xs text-muted sm:block">Soccer · MLB probability engine</p>
      </div>
    </header>
  );
}
