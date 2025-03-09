class ServerResponse {
  final List<Paper> articles;
  final String? audioFileName;
  final List<int>? audioBytes;
  final String? imageFileName;
  final List<int>? imageBytes;
  final String summary;

  ServerResponse({
    required this.articles,
    this.audioFileName,
    this.audioBytes,
    this.imageFileName,
    this.imageBytes,
    this.summary = '',
  });

  factory ServerResponse.fromJson(Map<String, dynamic> json) {
    print(json);
    return ServerResponse(
      articles: (json['selected_papers'] as List<dynamic>)
          .map((e) => Paper.fromJson(e as Map<String, dynamic>))
          .toList(),
      audioFileName: null,
      audioBytes: null,
      imageFileName: json['imageFileName'] as String?,
      imageBytes: null,
      summary: json['summary'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'articles': articles,
      'audioFileName': audioFileName,
      'audioBytes': audioBytes,
      'imageFileName': imageFileName,
      'imageBytes': imageBytes,
    };
  }
}

class Paper {
  final String title;
  final List<String> authors;
  final String url;
  final String summary;

  Paper({
    required this.title,
    required this.authors,
    required this.url,
    required this.summary,
  });

  factory Paper.fromJson(Map<String, dynamic> json) {
    return Paper(
      title: json['title'] as String,
      authors: (json['authors'] as List<dynamic>).map((e) => e as String).toList(),
      url: json['pdf_url'] as String,
      summary: json['summary'] as String,
    );
  }
}