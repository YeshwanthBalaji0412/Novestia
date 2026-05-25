export interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  onboarded: boolean;
  portfolio_id: string | null;
  created_at: string;
}

export interface OnboardResponse {
  user: UserResponse;
  portfolio_id: string;
}

export interface ApiResponse<T> {
  data: T;
}
