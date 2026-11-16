export interface ErrorResponseInterface {
  type: "validation_error" | "client_error" | "server_error";
  errors: { code: string; detail: string; attr: string | null }[];
}
