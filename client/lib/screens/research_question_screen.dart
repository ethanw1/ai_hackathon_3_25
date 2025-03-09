import 'package:client/model/server_response.dart';
import 'package:client/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:client/model/research_item.dart';
import 'package:client/provider/providers.dart';

class ResearchQuestionScreen extends StatefulWidget {
  final ResearchItem item;

  const ResearchQuestionScreen({super.key, required this.item});

  @override
  _ResearchQuestionScreenState createState() => _ResearchQuestionScreenState();
}

class _ResearchQuestionScreenState extends State<ResearchQuestionScreen> {
  void _confirmDelete() {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Delete Research Item'),
          content: Text('Are you sure you want to delete this research item?'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  researchItems.remove(widget.item);
                });
                Navigator.of(context).pop();
                Navigator.pop(context);
                Navigator.push(context, MaterialPageRoute(builder: (context) => HomeScreen()));
              },
              child: Text('Delete'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Research Question'),
        leading: IconButton(
          icon: Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.pop(context);
            Navigator.push(context, MaterialPageRoute(builder: (context) => HomeScreen()));
          },
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.delete),
            onPressed: _confirmDelete,
          ),
        ],
      ),
      body: Column(
        children: [
          // Display the original question, selected interests, and dates
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text('Original Question: ${widget.item.question}', style: TextStyle(fontSize: 24),),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text('Topic: ${widget.item.interests?.join(", ")}', style: TextStyle(fontSize: 18)),
          ),
          if (widget.item.timeRange != null) Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text('Date Range: ${widget.item.timeRange}'),
          ),
          // ... more UI elements ...
          Expanded(
            child: FutureBuilder(future: widget.item.getResponses(), builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return Center(child: CircularProgressIndicator());
              } else if (snapshot.hasError) {
                return Center(child: Text('Error: ${snapshot.error}'));
              } else {
                return ListView.builder(
                  itemCount: widget.item.responses.length,
                  itemBuilder: (context, index) {
                    final response = widget.item.responses[index];
                    return Column(
                      children:
                      [
                        Text("Executive Summary:", style: TextStyle(fontSize: 18)),
                        Text(response.summary),
                        SizedBox(height: 8),
                        for (int i = 0; i < response.articles.length; i++)
                          Column(
                            children: [
                              Text("Article $i", style: TextStyle(fontSize: 16)),
                              Text("Title: ${response.articles[i].title}"),
                              Text("URL: ${response.articles[i].url}"),
                              Text("Authors: ${response.articles[i].authors}"),
                              Text("Summary: ${response.articles[i].summary}"),
                              SizedBox(height: 8),
                            ],
                          ),
                        // ListView.builder(
                        //   shrinkWrap: true,
                        //   itemCount: response.articles.length,
                        //   itemBuilder: (context, index) {
                        //     final document = response.articles[index];
                        //     return Column(
                        //       children: [
                        //         Text("Title: ${document.title}"),
                        //         Text("URL: ${document.url}"),
                        //         Text("Authors: ${document.authors}"),
                        //         Text("Summary: ${document.summary}"),
                        //         SizedBox(height: 8),
                        //       ],
                        //     );
                        //   },
                        // ),
                      ],
                    );
                  },
                );
              }
            })
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Refresh the page
        },
        child: Icon(Icons.refresh),
      ),
    );
  }
}
