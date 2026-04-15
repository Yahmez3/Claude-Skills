import { Link } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { create } from "zustand";

type WatchlistState = {
  symbols: string[];
  add: (s: string) => void;
  remove: (s: string) => void;
};

const useWatchlist = create<WatchlistState>((set) => ({
  symbols: ["SPY", "QQQ", "AAPL", "NVDA", "BTC-USD"],
  add: (s) => set((st) => ({ symbols: [...new Set([...st.symbols, s.toUpperCase()])] })),
  remove: (s) => set((st) => ({ symbols: st.symbols.filter((x) => x !== s) })),
}));

export default function Watchlist() {
  const { symbols } = useWatchlist();
  return (
    <View style={{ flex: 1, backgroundColor: "#0a0a0a", padding: 16 }}>
      <FlatList
        data={symbols}
        keyExtractor={(s) => s}
        renderItem={({ item }) => (
          <Link href={`/symbol/${item}`} asChild>
            <Pressable style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: "#222" }}>
              <Text style={{ color: "#fff", fontSize: 18 }}>{item}</Text>
            </Pressable>
          </Link>
        )}
      />
    </View>
  );
}
