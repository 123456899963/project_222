import { describe, expect, it, vi } from 'vitest'
import { bootstrap } from './bootstrap'

function deferred() {
  let resolve!: () => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<void>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('bootstrap', () => {
  it('等待 hydrate 完成后才安装 router 并挂载', async () => {
    const order: string[] = []
    const gate = deferred()
    const app = { use: vi.fn(() => order.push('router')) }
    const mount = vi.fn(() => order.push('mount'))

    const running = bootstrap({
      app,
      router: {} as never,
      hydrate: () => {
        order.push('hydrate:start')
        return gate.promise.then(() => {
          order.push('hydrate:done')
        })
      },
      mount,
    })

    await Promise.resolve()
    expect(order).toEqual(['hydrate:start'])
    expect(app.use).not.toHaveBeenCalled()
    expect(mount).not.toHaveBeenCalled()

    gate.resolve()
    await running

    expect(order).toEqual(['hydrate:start', 'hydrate:done', 'router', 'mount'])
    expect(app.use).toHaveBeenCalledTimes(1)
    expect(mount).toHaveBeenCalledTimes(1)
  })

  it('hydrate 失败也继续安装与挂载，避免白屏', async () => {
    const app = { use: vi.fn() }
    const mount = vi.fn()

    await bootstrap({
      app,
      router: {} as never,
      hydrate: () => Promise.reject(new Error('network down')),
      mount,
    })

    expect(app.use).toHaveBeenCalledTimes(1)
    expect(mount).toHaveBeenCalledTimes(1)
  })
})
