import { QueryClient } from "@tanstack/react-query";

import { ApiRequestError } from "../api/client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      retry: (failureCount, error) => {
        // Never retry auth failures (the client already redirected) or 4xx.
        if (error instanceof ApiRequestError && error.status < 500)
          return false;
        return failureCount < 2;
      },
    },
  },
});
