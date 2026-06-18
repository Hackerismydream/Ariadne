export function assignTicketButtonLabel(state: string) {
  return state === "assigning" ? "分配中..." : "分配";
}
