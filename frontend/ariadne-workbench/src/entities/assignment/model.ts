export type AssignmentEntity = {
  id: string;
  ticketId: string;
  ticketKey: string;
  status: string;
  backendName?: string | null;
  targetProjectId?: string | null;
};
