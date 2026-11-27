import { authClient } from '#/lib/auth-client'
import { Avatar, AvatarFallback, AvatarImage } from '#/components/ui/avatar'
import { Button } from '#/components/ui/button'
import { Skeleton } from '#/components/ui/skeleton'

const BetterAuthHeader = () => {
  const { data: session, isPending } = authClient.useSession()

  if (isPending) {
    return <Skeleton className="size-8" />
  }

  if (session?.user) {
    const name = session.user.name || 'U'
    return (
      <div className="flex items-center gap-2">
        <Avatar>
          {session.user.image ? (
            <AvatarImage src={session.user.image} alt={name} />
          ) : null}
          <AvatarFallback>{name.charAt(0).toUpperCase()}</AvatarFallback>
        </Avatar>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            void authClient.signOut()
          }}
        >
          Keluar
        </Button>
      </div>
    )
  }

  return null
}

export default BetterAuthHeader
