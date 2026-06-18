export function addTicketCommentButtonLabel(state: string) {
  return state === "posting" ? "Posting..." : "Comment";
}
