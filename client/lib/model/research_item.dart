import 'package:client/model/server_response.dart';
import 'package:client/service/server.dart';

class ResearchItem {
  String? question;
  List<String>? interests;
  String? timeRange;
  List<ServerResponse> responses = [];

  Future<List<ServerResponse>> getResponses() async {
    if (responses.isEmpty) {
      responses = [ServerResponse.fromJson(await ServerService().getRequest('responses?question=$question&topic=${interests?.first}&time_frame=$timeRange'))];
    }
    return responses;
  }

  factory ResearchItem.fromJson(Map<String, dynamic> json) {
    return ResearchItem(
      question: json['question'] as String?,
      interests: (json['interests'] as List<dynamic>?)?.map((e) => e as String).toList(),
      timeRange: json['timeRange'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'question': question,
      'interests': interests,
      'timeRange': timeRange,
    };
  }
  ResearchItem({this.question, this.interests, this.timeRange});
}

class DateTimeRange {
  final DateTime start;
  final DateTime end;

  factory DateTimeRange.fromJson(Map<String, dynamic> json) {
    return DateTimeRange(
      start: DateTime.parse(json['start'] as String),
      end: DateTime.parse(json['end'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'start': start.toIso8601String(),
      'end': end.toIso8601String(),
    };
  }

  DateTimeRange({required this.start, required this.end});
}