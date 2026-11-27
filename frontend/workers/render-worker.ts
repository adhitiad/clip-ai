import { startRenderWorker } from '../src/server/queue'

const worker = await startRenderWorker()
console.log(`RabbitMQ render worker siap (${worker.name})`)
