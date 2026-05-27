// Bun's HTML bundler resolves asset imports (svg, png, etc.) to a hashed URL string.
// https://bun.com/docs/bundler/loaders#file
declare module "*.svg" {
  const url: string;
  export default url;
}
