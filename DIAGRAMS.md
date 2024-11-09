Pockyt Interaction Diagrams
-------------

### reg
Connecting pockyt to a Pocket account.

```mermaid
sequenceDiagram
    participant User as User
    participant Browser as Web Browser
    participant Client as Pockyt Client
    participant PocketAPI as Pocket API

    User->>Client: Run "pockyt reg"
    Client->>User: Display registration prompt
    User->>Browser: Open registration link
    Browser->>User: Display Pocket registration page
    User->>Browser: Register application
    Browser->>User: Provide Consumer Key
    User->>Client: Input Consumer Key
    Client->>PocketAPI: Obtain Request Token
    PocketAPI->>Client: Return Request Token
    Client->>User: Prompt for authorization
    User->>Browser: Open authorization link
    Browser->>User: Display authorization page
    User->>Browser: Authorize application
    Client->>PocketAPI: Request Access Token
    PocketAPI->>Client: Obtain Access Token and Username
    Client->>User: Registration complete
```

### get
get pocket collection, with useful item info

```mermaid
sequenceDiagram
    participant Client as Client
    participant System as System
    participant Network as Network
    participant Response as Response

    Client->>System: run("get")
    activate System
    System->>System: _validate_format()

    loop Process pages

        System->>Network: _api_request()
        activate Network
        Network->>Response: post_request(API.ENDPOINT, payload)
        activate Response
        Response-->>Network: Return response
        deactivate Response

        Network-->>System: Return _response
        deactivate Network


        System->>System: Extract items from response
        System->>System: Append items to all_items
        System->>System: Check pagination condition
    end

    System-->>Client: Output all_items
    deactivate System
```

### put
add to pocket collection, using links

```mermaid
sequenceDiagram
    participant Client as Client
    participant System as System
    participant Network as Network
    participant API as API

    Client->>System: run("put")
    activate System
    
    System->>System: _validate_format()
    
    System->>System: prepare payload
    System->>Network: _api_request()
    activate Network
    
    Network->>API: post_request(payload)
    activate API
    API->>Network: response
    deactivate API
    
    Network->>System: response
    deactivate Network
    
    System->>Client: Handle response
    deactivate System
```

### mod
modify pocket collection, using item ids

```mermaid
sequenceDiagram
    participant Client as Client
    participant System as System
    participant Network as Network
    participant Response as Response

    Client->>System: run("mod")
    activate System
    
    System->>System: Validate Format
    System->>Network: _api_request() with payload
    activate Network

    Network->>Network: post_request(API.MODIFY_URL, payload)
    Network-->>System: Response
    deactivate Network
    
    System->>System: Process Response (Update/Modify Collection)
    System-->>Client: Acknowledge Modification
    deactivate System
```