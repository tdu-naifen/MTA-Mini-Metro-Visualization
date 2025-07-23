namespace py mta_data
namespace js MtaData

// Geographic coordinates
struct Coordinate {
    1: double latitude,
    2: double longitude
}

// Train direction enum
enum Direction {
    NORTH = 1,
    SOUTH = 2,
    EAST = 3,
    WEST = 4,
    UNKNOWN = 5
}

// Train line colors (Mini Metro style)
enum LineColor {
    YELLOW = 1,  // N, Q, R, W lines
    RED = 2,
    BLUE = 3,
    GREEN = 4,
    ORANGE = 5,
    PURPLE = 6
}

// Station information
struct Station {
    1: string station_id,
    2: string name,
    3: Coordinate location,
    4: list<string> line_ids,
    5: bool is_terminus,
    6: optional string accessibility_info
}

// Train position and status
struct Train {
    1: string train_id,
    2: string line_id,
    3: Coordinate current_position,
    4: Direction direction,
    5: string current_station_id,
    6: optional string next_station_id,
    7: i64 timestamp,
    8: double speed_mph,
    9: string trip_id,
    10: optional i32 delay_seconds,
    11: LineColor line_color
}

// Station-to-station segment
struct LineSegment {
    1: string from_station_id,
    2: string to_station_id,
    3: list<Coordinate> path_coordinates,
    4: LineColor line_color,
    5: double distance_miles
}

// Complete line information
struct SubwayLine {
    1: string line_id,
    2: string name,
    3: LineColor color,
    4: list<Station> stations,
    5: list<LineSegment> segments,
    6: list<Train> active_trains
}

// Real-time feed data
struct RealTimeFeed {
    1: i64 timestamp,
    2: list<SubwayLine> lines,
    3: i32 total_active_trains,
    4: string feed_version
}

// WebSocket message types
enum MessageType {
    TRAIN_UPDATE = 1,
    STATION_UPDATE = 2,
    LINE_UPDATE = 3,
    FULL_REFRESH = 4,
    ERROR = 5
}

// WebSocket message
struct WebSocketMessage {
    1: MessageType type,
    2: i64 timestamp,
    3: optional Train train_data,
    4: optional Station station_data,
    5: optional SubwayLine line_data,
    6: optional RealTimeFeed full_data,
    7: optional string error_message
}

// API Response wrapper
struct ApiResponse {
    1: bool success,
    2: optional string error_message,
    3: optional RealTimeFeed data,
    4: i64 timestamp
}

// Exception types
exception MTAServiceException {
    1: string message,
    2: i32 error_code
}

exception InvalidLineException {
    1: string message,
    2: string line_id
}

exception FeedUnavailableException {
    1: string message,
    2: i64 retry_after_seconds
}

// Service definitions
service MTAFeedService {
    /**
     * Get real-time feed data for specific subway lines
     * @param line_ids: List of line IDs (e.g., ["N", "Q", "R", "W"])
     * @returns: Real-time feed data for requested lines
     * @throws: InvalidLineException if line not supported
     * @throws: FeedUnavailableException if MTA feed is down
     * @throws: MTAServiceException for other errors
     */
    RealTimeFeed getRealTimeFeed(1: list<string> line_ids) 
        throws (1: InvalidLineException invalid_line, 
                2: FeedUnavailableException feed_unavailable,
                3: MTAServiceException service_error),

    /**
     * Get all available subway lines with their static information
     * @returns: List of subway lines with stations and segments
     * @throws: MTAServiceException for service errors
     */
    list<SubwayLine> getAvailableLines() 
        throws (1: MTAServiceException service_error),

    /**
     * Get station information for a specific line
     * @param line_id: Line ID (e.g., "N", "Q", "R", "W")
     * @returns: List of stations for the line
     * @throws: InvalidLineException if line not supported
     * @throws: MTAServiceException for other errors
     */
    list<Station> getStationsForLine(1: string line_id) 
        throws (1: InvalidLineException invalid_line,
                2: MTAServiceException service_error),

    /**
     * Get active trains for a specific line
     * @param line_id: Line ID (e.g., "N", "Q", "R", "W")
     * @returns: List of active trains on the line
     * @throws: InvalidLineException if line not supported
     * @throws: FeedUnavailableException if MTA feed is down
     * @throws: MTAServiceException for other errors
     */
    list<Train> getActiveTrains(1: string line_id) 
        throws (1: InvalidLineException invalid_line,
                2: FeedUnavailableException feed_unavailable,
                3: MTAServiceException service_error),

    /**
     * Health check for the service
     * @returns: True if service is healthy
     */
    bool healthCheck(),

    /**
     * Get service status information
     * @returns: Service status and feed information
     */
    string getServiceStatus()
}

service WebSocketService {
    /**
     * Start real-time updates for specific lines
     * @param line_ids: List of line IDs to subscribe to
     * @param update_interval_seconds: Update frequency in seconds (default: 10)
     * @returns: Subscription ID for managing the subscription
     * @throws: InvalidLineException if line not supported
     * @throws: MTAServiceException for other errors
     */
    string subscribeToLineUpdates(1: list<string> line_ids, 2: i32 update_interval_seconds) 
        throws (1: InvalidLineException invalid_line,
                2: MTAServiceException service_error),

    /**
     * Stop real-time updates for a subscription
     * @param subscription_id: ID returned from subscribeToLineUpdates
     * @throws: MTAServiceException for service errors
     */
    void unsubscribeFromUpdates(1: string subscription_id) 
        throws (1: MTAServiceException service_error),

    /**
     * Get active subscription information
     * @returns: List of active subscription IDs
     */
    list<string> getActiveSubscriptions()
}
