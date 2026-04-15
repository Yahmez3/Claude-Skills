# Trading Mobile (React Native + Expo)

Expo Router app with watchlist and per-symbol chart screen.

## Run

```bash
pnpm install
pnpm start
```

Press `i` for iOS simulator, `a` for Android, `w` for web.

Point `EXPO_PUBLIC_BACKEND_URL` at your FastAPI backend.

## Extend

- Charts: `pnpm add react-native-wagmi-charts react-native-reanimated react-native-gesture-handler`
- Auth: `pnpm add @clerk/clerk-expo`
- Push alerts: `pnpm add expo-notifications`
- Credentials: already installed `expo-secure-store` — store broker API keys there

## Deploy

- iOS / Android builds: `eas build`
- Web: `pnpm expo export -p web` and deploy to any static host
