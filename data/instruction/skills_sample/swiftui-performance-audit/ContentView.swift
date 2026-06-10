import SwiftUI

struct ContentView: View {
    @State private var items: [Item] = []
    @State private var searchText = ""
    
    var filteredItems: [Item] {
        if searchText.isEmpty {
            return items
        }
        return items.filter { $0.name.lowercased().contains(searchText.lowercased()) }
    }
    
    var body: some View {
        NavigationView {
            List(filteredItems) { item in
                ItemRow(item: item)
            }
            .searchable(text: $searchText)
            .navigationTitle("Items (\(filteredItems.count))")
            .onAppear {
                loadItems()
            }
        }
    }
    
    func loadItems() {
        // Synchronous heavy computation on main thread
        items = (0..<10000).map { i in
            Item(id: i, name: "Item \(i)", description: String(repeating: "x", count: 500))
        }
    }
}

struct ItemRow: View {
    let item: Item
    var body: some View {
        VStack(alignment: .leading) {
            Text(item.name).font(.headline)
            Text(item.description).font(.caption).lineLimit(2)
        }
    }
}

struct Item: Identifiable {
    let id: Int
    let name: String
    let description: String
}
