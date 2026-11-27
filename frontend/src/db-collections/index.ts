import {
  createCollection,
  localOnlyCollectionOptions,
} from '@tanstack/react-db'
import { z } from 'zod'

const MessageSchema = z.object({
  id: z.number(),
  text: z.string(),
  user: z.string(),
})

export type Message = z.infer<typeof MessageSchema>

export const messagesCollection = createCollection(
  localOnlyCollectionOptions({
    getKey: (message) => message.id,
    schema: MessageSchema,
  }),
)

const SavedProviderSchema = z.object({
  id: z.string(),
  name: z.string(),
})

export type SavedProvider = z.infer<typeof SavedProviderSchema>

export const savedProvidersCollection = createCollection(
  localOnlyCollectionOptions({
    getKey: (provider) => provider.id,
    schema: SavedProviderSchema,
  }),
)
