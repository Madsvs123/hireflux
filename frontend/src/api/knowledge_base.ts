import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type KnowledgeArticleStatus = 'draft' | 'published' | 'archived'

export interface KnowledgeCategory {
  id: string
  organization: string
  name: string
  slug: string
  description: string
  icon: string
  order: number
  is_active: boolean
  article_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeArticle {
  id: string
  organization: string
  category: string
  category_name: string | null
  title: string
  slug: string
  summary: string
  body_html: string
  status: KnowledgeArticleStatus
  view_count: number
  published_at: string | null
  published_by: string | null
  published_by_name: string | null
  updated_by: string | null
  comment_count: number
  vote_count: number
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeArticleVersion {
  id: string
  organization: string
  article: string
  version_number: number
  title: string
  body_html: string
  change_note: string
  created_by: string | null
  created_by_name: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeComment {
  id: string
  organization: string
  article: string
  article_title: string
  author: string | null
  author_name: string | null
  body: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ArticleVote {
  id: string
  organization: string
  article: string
  article_title: string
  user: string | null
  helpful: boolean
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ArticleAttachment {
  id: string
  organization: string
  article: string
  name: string
  file: string | null
  size: number | null
  uploaded_by: string | null
  uploaded_by_name: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeSearchResults {
  query: string
  count: number
  results: KnowledgeArticle[]
}

export const knowledgeBaseApi = {
  categories: {
    list: (params?: ListParams) =>
      get<Paginated<KnowledgeCategory>>('/knowledge-categories/', params),
    get: (id: string) => get<KnowledgeCategory>(`/knowledge-categories/${id}/`),
    create: (data: Partial<KnowledgeCategory>) =>
      post<KnowledgeCategory>('/knowledge-categories/', data),
    update: (id: string, data: Partial<KnowledgeCategory>) =>
      patch<KnowledgeCategory>(`/knowledge-categories/${id}/`, data),
    remove: (id: string) => del(`/knowledge-categories/${id}/`),
  },
  articles: {
    list: (params?: ListParams) =>
      get<Paginated<KnowledgeArticle>>('/knowledge-articles/', params),
    get: (id: string) => get<KnowledgeArticle>(`/knowledge-articles/${id}/`),
    create: (data: Partial<KnowledgeArticle>) =>
      post<KnowledgeArticle>('/knowledge-articles/', data),
    update: (id: string, data: Partial<KnowledgeArticle>) =>
      patch<KnowledgeArticle>(`/knowledge-articles/${id}/`, data),
    remove: (id: string) => del(`/knowledge-articles/${id}/`),
    publish: (id: string) => post<KnowledgeArticle>(`/knowledge-articles/${id}/publish/`, {}),
    archive: (id: string) => post<KnowledgeArticle>(`/knowledge-articles/${id}/archive/`, {}),
    restoreVersion: (id: string, data: { version_id: string }) =>
      post<KnowledgeArticle>(`/knowledge-articles/${id}/restore-version/`, data),
    incrementView: (id: string) =>
      post<{ view_count: number }>(`/knowledge-articles/${id}/increment-view/`, {}),
    versions: (id: string) =>
      get<KnowledgeArticleVersion[]>(`/knowledge-articles/${id}/versions/`),
    diff: (id: string, data: { version_a: string; version_b: string }) =>
      post<{ from_version: number; to_version: number; title_diff: string[]; body_diff: string[] }>(
        `/knowledge-articles/${id}/diff/`,
        data,
      ),
  },
  comments: {
    list: (params?: ListParams) => get<Paginated<KnowledgeComment>>('/knowledge-comments/', params),
    get: (id: string) => get<KnowledgeComment>(`/knowledge-comments/${id}/`),
    create: (data: Partial<KnowledgeComment>) =>
      post<KnowledgeComment>('/knowledge-comments/', data),
    update: (id: string, data: Partial<KnowledgeComment>) =>
      patch<KnowledgeComment>(`/knowledge-comments/${id}/`, data),
    remove: (id: string) => del(`/knowledge-comments/${id}/`),
  },
  votes: {
    list: (params?: ListParams) => get<Paginated<ArticleVote>>('/knowledge-votes/', params),
    get: (id: string) => get<ArticleVote>(`/article-votes/${id}/`),
    create: (data: Partial<ArticleVote>) => post<ArticleVote>('/article-votes/', data),
    remove: (id: string) => del(`/article-votes/${id}/`),
    toggle: (data: { article: string; helpful: boolean }) =>
      post<ArticleVote>('/article-votes/toggle/', data),
  },
  attachments: {
    list: (params?: ListParams) =>
      get<Paginated<ArticleAttachment>>('/article-attachments/', params),
    get: (id: string) => get<ArticleAttachment>(`/article-attachments/${id}/`),
    create: (data: Partial<ArticleAttachment>) =>
      post<ArticleAttachment>('/article-attachments/', data),
    upload: (form: FormData) => post<ArticleAttachment>('/article-attachments/', form),
    update: (id: string, data: Partial<ArticleAttachment>) =>
      patch<ArticleAttachment>(`/article-attachments/${id}/`, data),
    remove: (id: string) => del(`/article-attachments/${id}/`),
  },
  search: (params?: ListParams) => get<KnowledgeSearchResults>('/knowledge-search/', params),
}
