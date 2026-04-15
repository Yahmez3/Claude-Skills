import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";

const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function SymbolScreen() {
  const { ticker } = useLocalSearchParams<{ ticker: string }>();
  const [bars, setBars] = useState<any[] | null>(null);

  useEffect(() => {
    fetch(`${BACKEND}/bars?symbol=${ticker}&timeframe=1d`)
      .then((r) => r.json())
      .then((j) => setBars(j.bars))
      .catch(() => setBars([]));
  }, [ticker]);

  if (bars === null) {
    return (
      <View style={{ flex: 1, backgroundColor: "#0a0a0a", justifyContent: "center" }}>
        <ActivityIndicator color="#fff" />
      </View>
    );
  }
  const last = bars[bars.length - 1];
  const prev = bars[bars.length - 2];
  const chg = last && prev ? (last.c / prev.c - 1) * 100 : 0;

  return (
    <View style={{ flex: 1, backgroundColor: "#0a0a0a", padding: 16 }}>
      <Text style={{ color: "#fff", fontSize: 32, fontWeight: "bold" }}>{ticker}</Text>
      {last && (
        <>
          <Text style={{ color: "#fff", fontSize: 28, marginTop: 8 }}>
            ${last.c.toFixed(2)}
          </Text>
          <Text style={{ color: chg >= 0 ? "#4ade80" : "#f87171", fontSize: 18 }}>
            {chg >= 0 ? "+" : ""}{chg.toFixed(2)}% today
          </Text>
        </>
      )}
      <Text style={{ color: "#888", marginTop: 16 }}>
        {bars.length} bars loaded. Drop in react-native-wagmi-charts here for the candlestick view.
      </Text>
    </View>
  );
}
