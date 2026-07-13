import { expect, test } from '@playwright/test'

test('renders the agent workspace on desktop', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '创作台' })).toBeVisible()
  await expect(page.locator('.agent-node')).toHaveCount(5)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440)
  await page.screenshot({ path: '/tmp/nanguos-desktop.png', fullPage: true })
})

test('keeps controls readable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  await expect(page.getByRole('button', { name: '召集乐团开始创作' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/nanguos-mobile.png', fullPage: true })
})
