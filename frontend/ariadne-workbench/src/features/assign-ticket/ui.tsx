export function assignTicketButtonLabel(state: string) {
  return state === "assigning" ? "Assigning..." : "Assign";
}
