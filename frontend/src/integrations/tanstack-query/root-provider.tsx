import { QueryClient } from '@tanstack/react-query'

export const getContext = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  })

  return {
    queryClient,
  }
}

const TanstackQueryProvider = () => {}

export default TanstackQueryProvider
