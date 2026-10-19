import { del, get, patch, post, put } from './http'
import type { ListParams, Paginated } from './types'

export interface BrandProfile {
  id: string
  organization: string
  primary_color: string
  secondary_color: string
  logo: string | null
  tagline: string
  about_html: string
  culture_values: string[]
  is_published: boolean
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CareerSiteConfig {
  id: string
  organization: string
  site_name: string
  slug: string
  enabled: boolean
  hero_title: string
  hero_subtitle: string
  hero_image: string | null
  footer_text: string
  custom_css: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface TeamPage {
  id: string
  name: string
  role: string
  bio: string
  photo: string | null
  order: number
  is_active: boolean
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface Testimonial {
  id: string
  author_name: string
  author_role: string
  content: string
  rating: number
  is_active: boolean
  order: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type CulturePostStatus = 'draft' | 'published' | 'archived'

export interface CulturePost {
  id: string
  title: string
  body_html: string
  cover_image: string | null
  tags: string[]
  status: CulturePostStatus
  published_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface PublicCareersSite {
  slug: string
  site_name: string
  hero_title: string
  hero_subtitle: string
  hero_image: string | null
  footer_text: string
  custom_css: string
  brand: {
    primary_color: string | null
    secondary_color: string | null
    logo: string | null
    tagline: string
    about_html: string
    culture_values: string[]
  }
  team: TeamPage[]
  testimonials: Testimonial[]
  culture_posts: CulturePost[]
  jobs: Array<{
    id: string
    title: string
    slug: string
    employment_type: string
    remote_policy: string
    [key: string]: unknown
  }>
}

export const brandingApi = {
  // Brand profile (one-to-one: list returns the single profile, POST upserts)
  getProfile: () => get<BrandProfile>('/brand-profile/'),
  saveProfile: (data: Partial<BrandProfile>) => post<BrandProfile>('/brand-profile/', data),
  updateProfile: (id: string, data: Partial<BrandProfile>) =>
    put<BrandProfile>(`/brand-profile/${id}/`, data),
  publishProfile: () => post<BrandProfile>('/brand-profile/publish/'),
  unpublishProfile: () => post<BrandProfile>('/brand-profile/unpublish/'),

  // Career site config (one-to-one, same upsert semantics)
  getCareerSite: () => get<CareerSiteConfig>('/career-site-config/'),
  saveCareerSite: (data: Partial<CareerSiteConfig>) =>
    post<CareerSiteConfig>('/career-site-config/', data),
  updateCareerSite: (id: string, data: Partial<CareerSiteConfig>) =>
    patch<CareerSiteConfig>(`/career-site-config/${id}/`, data),
  publishCareerSite: () => post<CareerSiteConfig>('/career-site-config/publish/'),

  // Team pages
  listTeam: (params?: ListParams) => get<Paginated<TeamPage>>('/team-pages/', params),
  getTeam: (id: string) => get<TeamPage>(`/team-pages/${id}/`),
  createTeam: (data: Partial<TeamPage>) => post<TeamPage>('/team-pages/', data),
  updateTeam: (id: string, data: Partial<TeamPage>) => patch<TeamPage>(`/team-pages/${id}/`, data),
  removeTeam: (id: string) => del(`/team-pages/${id}/`),

  // Testimonials
  listTestimonials: (params?: ListParams) => get<Paginated<Testimonial>>('/testimonials/', params),
  getTestimonial: (id: string) => get<Testimonial>(`/testimonials/${id}/`),
  createTestimonial: (data: Partial<Testimonial>) => post<Testimonial>('/testimonials/', data),
  updateTestimonial: (id: string, data: Partial<Testimonial>) =>
    patch<Testimonial>(`/testimonials/${id}/`, data),
  removeTestimonial: (id: string) => del(`/testimonials/${id}/`),

  // Culture posts
  listCulturePosts: (params?: ListParams) => get<Paginated<CulturePost>>('/culture-posts/', params),
  getCulturePost: (id: string) => get<CulturePost>(`/culture-posts/${id}/`),
  createCulturePost: (data: Partial<CulturePost>) => post<CulturePost>('/culture-posts/', data),
  updateCulturePost: (id: string, data: Partial<CulturePost>) =>
    patch<CulturePost>(`/culture-posts/${id}/`, data),
  removeCulturePost: (id: string) => del(`/culture-posts/${id}/`),
  publishCulturePost: (id: string) => post<CulturePost>(`/culture-posts/${id}/publish/`),
  archiveCulturePost: (id: string) => post<CulturePost>(`/culture-posts/${id}/archive/`),

  // Public careers site payload (anonymous read)
  publicCareersSite: (slug: string) => get<PublicCareersSite>(`/public/careers-site/${slug}/`),
}
