function borderClasses(border) {
  return border === "on" ? "border border-border" : "border-0";
}

function bgClasses(bg) {
  return bg === "card" ? "bg-card-surface" : "bg-background";
}

function paddingClasses(p) {
  switch (p) {
    case "none":
      return "p-0";
    case "sm":
      return "p-3";
    case "lg":
      return "p-6";
    case "md":
    default:
      return "p-5";
  }
}

function shadowClasses(s) {
  switch (s) {
    case "none":
      return "shadow-none";
    case "md":
      return "shadow-md";
    case "sm":
    default:
      return "shadow-sm";
  }
}

function radiusClasses(r) {
  switch (r) {
    case "none":
      return "rounded-none";
    case "md":
      return "rounded-md";
    case "2xl":
      return "rounded-2xl";
    case "xl":
    default:
      return "rounded-xl";
  }
}

export function Card({
  children,
  border = "on",
  bg = "card",
  padding = "md",
  shadow = "sm",
  radius = "xl",
  className = "",
  ...props
}) {
  return (
    <div
      className={[
        bgClasses(bg),
        borderClasses(border),
        paddingClasses(padding),
        shadowClasses(shadow),
        radiusClasses(radius),
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;