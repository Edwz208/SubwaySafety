export function Button({
  variant = "primary",
  size = "md",
  radius,
  fullWidth = false,
  icon,
  layout = "default",
  className,
  type,
  children,
  ...props
}) {

  const resolvedType = type ?? "button"

  const classes = [
    "inline-flex items-center justify-center font-medium transition",
    "outline-none",
    "focus-visible:ring-2 focus-visible:ring-offset-2",
    "disabled:opacity-50 disabled:pointer-events-none",
  ]

  /* ---------- Radius ---------- */
  if (radius) classes.push(`rounded-${radius}`)
  else classes.push("rounded")

  /* ---------- Size ---------- */
  if (size === "xs") classes.push("px-3 py-2 text-sm")
  if (size === "sm") classes.push("px-4 py-2 text-sm")
  if (size === "md") classes.push("p-3 text-[0.875rem]")
  if (size === "lg") classes.push("px-4 py-3 text-base")
  if (size === "xl") classes.push("px-6 py-3 text-[0.875rem]")
  if (size === "xxl") classes.push("p-6 text-base")

  /* ---------- Layout ---------- */
  if (layout === "default") classes.push("gap-2")
  if (layout === "stacked") classes.push("flex-col items-center justify-center")


  if (fullWidth) classes.push("w-full")

  /* ---------- Variants ---------- */
if (variant === "primary") {
  classes.push(
    "bg-accent text-white",
    "hover:opacity-90",
    "focus-visible:ring-accent"
  )
}

if (variant === "outline") {
  classes.push(
    "border border-border",
    "text-primary",
    "bg-card-surface",
    "hover:bg-border/20",
    "focus-visible:ring-border"
  )
}

if (variant === "danger") {
  classes.push(
    "bg-danger text-white",
    "hover:opacity-90",
    "focus-visible:ring-danger"
  )
}

if (variant === "success") {
  classes.push(
    "bg-success text-white",
    "hover:opacity-90",
    "focus-visible:ring-success"
  )
}

  if (className) classes.push(className)

  const iconClass =
    layout === "stacked"
      ? "h-6 w-6 shrink-0"
      : "h-4 w-4 shrink-0"

  const leftIcon = icon ? (
    icon === "plus" ? (
      <span className={`${iconClass} inline-flex items-center justify-center`}>
        +
      </span>
    ) : (
      <img
        src={`/icons/${icon}.svg`}
        alt=""
        aria-hidden="true"
        className={iconClass}
      />
    )
  ) : null

  return (
    <button type={resolvedType} className={classes.join(" ")} {...props}>
      {leftIcon}
      {children && <span>{children}</span>}
    </button>
  )
}

export default Button
