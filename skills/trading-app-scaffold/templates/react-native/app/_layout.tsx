import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerStyle: { backgroundColor: "#0a0a0a" }, headerTintColor: "#fff" }}>
      <Stack.Screen name="index" options={{ title: "Watchlist" }} />
      <Stack.Screen name="symbol/[ticker]" options={{ title: "Chart" }} />
    </Stack>
  );
}
