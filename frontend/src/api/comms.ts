import { get, post, patch } from './http'
import type { ListParams, Message, MessageThread, Paginated } from './types'

export const commsApi = {
  listThreads: (params?: ListParams) => get<Paginated<MessageThread>>('/message-threads/', params),
  getThread: (id: string) => get<MessageThread>(`/message-threads/${id}/`),
  createThread: (data: {
    subject: string
    participant_ids: string[]
    body: string
  }) => post<MessageThread>('/message-threads/', data),
  listMessages: (threadId: string, params?: ListParams) =>
    get<Paginated<Message>>(`/message-threads/${threadId}/message/`, params),
  sendMessage: (threadId: string, body: string) =>
    post<Message>(`/message-threads/${threadId}/messages/`, { message: body }),
  markRead: (threadId: string) => patch(`/message-threads/${threadId}/read/`, {}),

  listTemplates: (params?: ListParams) =>
    get<Paginated<Record<string, unknown>>>('/email-templates/', params),
  createTemplate: (data: Record<string, unknown>) => post('/email-templates/', data),
  updateTemplate: (id: string, data: Record<string, unknown>) =>
    patch(`/email-templates/${id}/`, data),
}
