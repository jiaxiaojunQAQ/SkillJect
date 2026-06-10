import Foundation

class NetworkManager {
    static let shared = NetworkManager()
    private var activeTasks: [String: URLSessionDataTask] = [:]
    
    func fetchUser(id: Int, completion: @escaping (Result<User, Error>) -> Void) {
        let task = URLSession.shared.dataTask(with: URL(string: "https://api.example.com/users/\(id)")!) { data, _, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            let user = try! JSONDecoder().decode(User.self, from: data!)
            DispatchQueue.main.async {
                completion(.success(user))
            }
        }
        activeTasks["\(id)"] = task
        task.resume()
    }
    
    func cancelFetch(id: Int) {
        activeTasks["\(id)"]?.cancel()
        activeTasks.removeValue(forKey: "\(id)")
    }
}

struct User: Codable {
    let id: Int
    let name: String
    let email: String
}
