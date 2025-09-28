export type BroadcastRequest = {
  channels: string[];
  html: string;
};

export type BroadcastResponse = {
  id: string;
  status: string;
  sentAt: string | null;
};
