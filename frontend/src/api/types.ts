/** Shared HireFlux API types */

export type UUID = string

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiErrorBody {
  detail?: string
  message?: string
  [key: string]: unknown
}

export type UserType = 'staff' | 'candidate' | 'admin'

export interface User {
  id: UUID
  email: string
  first_name: string
  last_name: string
  full_name: string
  user_type: UserType
  phone?: string
  avatar?: string | null
  timezone?: string
  is_email_verified: boolean
  is_active: boolean
  last_login_at?: string | null
  created_at: string
  updated_at: string
  memberships?: Membership[]
}

export interface Organization {
  id: UUID
  name: string
  slug: string
  org_type: string
  logo?: string | null
  website?: string
  industry?: string
  size?: string
  settings?: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Role {
  id: UUID
  organization: UUID
  name: string
  slug: string
  description: string
  permissions: string[]
  is_system: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Membership {
  id: UUID
  organization: Organization
  user: User
  role: Role | null
  title?: string
  is_owner: boolean
  is_active: boolean
  permissions: string[]
  joined_at: string
  created_at: string
  updated_at: string
}

export interface Invitation {
  id: UUID
  organization: UUID
  organization_name: string
  email: string
  role: Role | null
  invited_by?: User | null
  status: string
  message: string
  expires_at: string
  accepted_at?: string | null
  created_at: string
  updated_at: string
}

export interface Department {
  id: UUID
  organization: UUID
  name: string
  parent?: UUID | null
  parent_name?: string | null
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Office {
  id: UUID
  organization: UUID
  name: string
  address_line1: string
  address_line2: string
  city: string
  state: string
  postal_code: string
  country: string
  timezone: string
  is_headquarters: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface HiringTeamMember {
  id: UUID
  team: UUID
  user: UUID
  user_email: string
  user_name: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface HiringTeam {
  id: UUID
  organization: UUID
  name: string
  description: string
  department?: UUID | null
  department_name?: string | null
  is_active: boolean
  members: HiringTeamMember[]
  created_at: string
  updated_at: string
}

export type JobStatus =
  | 'draft'
  | 'pending_approval'
  | 'published'
  | 'paused'
  | 'closed'
  | 'archived'

export interface JobListItem {
  id: UUID
  title: string
  slug: string
  department?: UUID | null
  department_name?: string | null
  office?: UUID | null
  office_name?: string | null
  employment_type: string
  experience_level: string
  status: JobStatus
  salary_min?: string | null
  salary_max?: string | null
  currency: string
  salary_visible: boolean
  openings: number
  remote_policy: string
  hiring_manager?: UUID | null
  hiring_manager_email?: string | null
  published_at?: string | null
  closes_at?: string | null
  career_page_visible: boolean
  recruiter_count: number
  created_at: string
  updated_at: string
}

export interface ScreeningQuestion {
  id: UUID
  job: UUID
  prompt: string
  question_type: string
  options: unknown[]
  is_required: boolean
  is_knockout: boolean
  knockout_answer?: string
  order: number
  help_text: string
  created_at: string
  updated_at: string
}

export interface JobApproval {
  id: UUID
  job: UUID
  requested_by?: UUID | null
  approver?: UUID | null
  decided_by?: UUID | null
  decision: string
  comment: string
  decided_at?: string | null
  created_at: string
  updated_at: string
}

export interface Job extends Omit<JobListItem, 'department_name' | 'office_name' | 'hiring_manager_email' | 'recruiter_count'> {
  description: string
  requirements: string
  responsibilities: string
  required_skills: string[]
  preferred_skills: string[]
  custom_fields: Record<string, unknown>
  pipeline_template?: UUID | null
  screening_questions: ScreeningQuestion[]
  recruiters: Array<{
    id: UUID
    job: UUID
    user: UUID
    user_email: string
    user_name: string
    is_primary: boolean
    notes: string
  }>
  approvals: JobApproval[]
  created_by?: UUID | null
  updated_by?: UUID | null
}

export interface CandidateListItem {
  id: UUID
  name: string
  full_name: string
  first_name: string
  last_name: string
  email: string
  phone?: string
  location?: string
  headline?: string
  source?: string
  tags: string[]
  skills: string[]
  years_experience?: number | null
  is_talent_pool: boolean
  do_not_hire: boolean
  duplicate_of?: UUID | null
  created_at: string
  updated_at: string
}

export interface CandidateEducation {
  id: UUID
  candidate: UUID
  institution: string
  degree: string
  field_of_study: string
  start_date?: string | null
  end_date?: string | null
  is_current: boolean
  description: string
  gpa?: string | null
}

export interface CandidateExperience {
  id: UUID
  candidate: UUID
  company: string
  title: string
  location: string
  start_date?: string | null
  end_date?: string | null
  is_current: boolean
  description: string
  skills_used: string[]
}

export interface CandidateDocument {
  id: UUID
  candidate: UUID
  doc_type: string
  title: string
  file?: string | null
  file_name: string
  content_type: string
  file_size: number
  parse_status: string
  is_primary: boolean
  created_at: string
}

export interface CandidateNote {
  id: UUID
  candidate: UUID
  body: string
  visibility: string
  pinned: boolean
  created_by?: UUID | null
  author_email?: string
  created_at: string
  updated_at: string
}

export interface Candidate extends CandidateListItem {
  user?: UUID | null
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  website_url?: string
  summary?: string
  salary_expectation_min?: string | null
  salary_expectation_max?: string | null
  salary_currency?: string
  do_not_hire_reason?: string
  custom_fields: Record<string, unknown>
  education: CandidateEducation[]
  experience: CandidateExperience[]
  certifications: Array<Record<string, unknown>>
  documents: CandidateDocument[]
  notes: CandidateNote[]
}

export interface PipelineStage {
  id: UUID
  template: UUID
  name: string
  stage_type: string
  order: number
  color: string
  is_terminal: boolean
  auto_reject_days?: number | null
  allowed_next_stage_ids: UUID[]
  automation_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PipelineTemplate {
  id: UUID
  name: string
  description: string
  is_default: boolean
  is_active: boolean
  stages: PipelineStage[]
  created_at: string
  updated_at: string
}

export interface ApplicationListItem {
  id: UUID
  job: UUID
  job_title: string
  candidate: UUID
  candidate_name: string
  candidate_email: string
  stage?: UUID | null
  stage_name?: string | null
  stage_type?: string | null
  status: string
  relevance_score?: number | null
  knockout_failed: boolean
  tags: string[]
  applied_at: string
  stage_entered_at?: string | null
  created_at: string
}

export interface Application extends Omit<ApplicationListItem, 'stage_name' | 'stage_type'> {
  answers: Record<string, unknown>
  source: string
  rejected_at?: string | null
  rejection_reason?: string
  hired_at?: string | null
  cover_letter: string
  metadata: Record<string, unknown>
  stage_history: Array<{
    id: UUID
    from_stage?: UUID | null
    to_stage: UUID
    from_stage_name?: string | null
    to_stage_name?: string | null
    note: string
    duration_seconds?: number | null
    created_at: string
  }>
  activities: Array<{
    id: UUID
    activity_type: string
    message: string
    metadata: Record<string, unknown>
    created_at: string
  }>
  updated_at: string
}

export interface BoardApplication {
  id: UUID
  candidate: UUID
  candidate_name: string
  candidate_email: string
  headline?: string
  relevance_score?: number | null
  status: string
  tags: string[]
  applied_at: string
  stage_entered_at?: string | null
  knockout_failed: boolean
}

export interface BoardColumn {
  stage: PipelineStage
  applications: BoardApplication[]
}

export interface Notification {
  id: UUID
  organization: UUID
  title: string
  body: string
  level: string
  category: string
  link?: string
  data: Record<string, unknown>
  is_read: boolean
  read_at?: string | null
  created_at: string
  updated_at: string
}

export interface Interview {
  id: UUID
  application: UUID
  job_title?: string
  candidate_name?: string
  title: string
  interview_type: string
  status: string
  scheduled_at: string
  duration_minutes: number
  location?: string
  meeting_url?: string
  interviewers: UUID[]
  scorecard?: InterviewScorecard | null
  notes?: string
  created_at: string
  updated_at: string
}

export interface InterviewScorecard {
  overall_rating?: number
  recommendation?: string
  competencies: Array<{ name: string; rating: number; notes?: string }>
  comments?: string
  submitted_at?: string | null
}

export interface AssessmentTemplate {
  id: UUID
  name: string
  description: string
  assessment_type: string
  duration_minutes: number
  questions: Array<{ id?: string; prompt: string; question_type: string; options?: string[] }>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AssessmentAssignment {
  id: UUID
  template: UUID
  template_name?: string
  application: UUID
  candidate_name?: string
  job_title?: string
  status: string
  due_at?: string | null
  score?: number | null
  started_at?: string | null
  completed_at?: string | null
  created_at: string
  updated_at: string
}

export interface Offer {
  id: UUID
  application: UUID
  candidate_name?: string
  job_title?: string
  status: string
  salary: string
  currency: string
  start_date?: string | null
  equity?: string
  bonus?: string
  benefits?: string
  notes?: string
  approval_status: string
  sent_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  created_at: string
  updated_at: string
}

export interface TalentPool {
  id: UUID
  name: string
  description: string
  candidate_count: number
  tags: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Referral {
  id: UUID
  candidate_name: string
  candidate_email: string
  job?: UUID | null
  job_title?: string
  referred_by_name: string
  status: string
  notes: string
  created_at: string
}

export interface MessageThread {
  id: UUID
  subject: string
  participants: Array<{ id: UUID; name: string; email: string }>
  last_message?: string
  last_message_at?: string | null
  unread_count: number
  created_at: string
}

export interface Message {
  id: UUID
  thread: UUID
  body: string
  sender_name: string
  sender_id: UUID
  created_at: string
}

export interface AnalyticsOverview {
  open_jobs: number
  active_candidates: number
  applications_this_month: number
  interviews_scheduled: number
  offers_pending: number
  hires_this_month: number
  avg_time_to_hire_days: number
  funnel: Array<{ stage: string; count: number }>
  sources: Array<{ source: string; count: number }>
  time_to_hire_by_dept: Array<{ department: string; days: number }>
}

export interface SearchResults {
  jobs: JobListItem[]
  candidates: CandidateListItem[]
  application_results: ApplicationListItem[]
}

export interface CandidateJobMatch {
  id: UUID
  candidate: UUID
  job: UUID
  candidate_name?: string
  job_title?: string
  score: number
  breakdown: Record<string, unknown>
  created_at: string
}

export interface LoginResponse {
  access: string
  refresh?: string
  user: User
}

export interface RegisterPayload {
  email: string
  password: string
  first_name?: string
  last_name?: string
  organization_name: string
  org_type?: string
  website?: string
  industry?: string
  size?: string
}

export interface ListParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | undefined | null
}
