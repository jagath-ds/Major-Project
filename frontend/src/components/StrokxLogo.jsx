import strokxEmblem from "../assets/strokx-emblem.png";

// ── Smart Emblem ──
export function StrokxEmblem({ size = "md" }) {
  const sizes = {
    xs: "w-3.5 h-3.5",
    sm: "w-5 h-5",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };
  return (
    <img
      src={strokxEmblem}
      alt="Strokx"
      className={`${sizes[size]} object-contain`}
    />
  );
}

// ── Full Logo: emblem + text ──
export function StrokxLogoFull({ isDark }) {
  return (
    <div className="flex items-center gap-3">
      <div
      >
        <StrokxEmblem size="md" />
      </div>
      <div className="flex flex-col leading-none gap-0.5">
        <span
          className={`font-black text-[15px] tracking-[0.12em] uppercase ${
            isDark ? "text-white" : "text-slate-900"
          }`}
        >
          Strokx
        </span>
        <span
          className={`text-[9px] font-semibold tracking-[0.25em] uppercase ${
            isDark ? "text-blue-400/80" : "text-blue-500"
          }`}
        >
          Technologies
        </span>
      </div>
    </div>
  );
}

// ── Chat Avatar ──
export function StrokxAvatar({ isDark }) {
  return (
    <div
      className={`w-8 h-8 rounded-full flex items-center justify-center shadow-md border ${
        isDark ? "bg-[#1a1a2e] border-white/10" : "bg-white border-blue-100"
      }`}
    >
      <StrokxEmblem size="sm" />
    </div>
  );
}

// ── Welcome Hero Icon ──
export function StrokxHeroIcon({ isDark }) {
  return (
    <div className="relative">
      <div
        className={`absolute inset-0 rounded-3xl blur-2xl opacity-40 scale-110 ${
          isDark ? "bg-blue-500" : "bg-blue-300"
        }`}
      />
      <div
      >
        <StrokxEmblem size="lg" />
      </div>
    </div>
  );
}
