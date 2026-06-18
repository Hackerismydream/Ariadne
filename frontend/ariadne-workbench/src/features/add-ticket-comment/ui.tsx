export function addTicketCommentButtonLabel(state: string) {
  return state === "posting" ? "发送中..." : "评论";
}
