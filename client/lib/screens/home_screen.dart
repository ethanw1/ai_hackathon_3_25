import 'package:client/model/research_item.dart';
import 'package:client/screens/research_question_screen.dart';
import 'package:flutter/material.dart';
import "package:client/provider/providers.dart";

class HomeScreen extends StatelessWidget {
  HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Research Assistant'),
              ),
      body: ListView.builder(
        itemCount: researchItems.length,
        itemBuilder: (context, index) {
          final item = researchItems[index];
          return ListTile(
            title: Text(item.question ?? item.interests?.join(", ") ?? "No question"),
            onTap: () {
              Navigator.push(context, MaterialPageRoute(builder: (context) => ResearchQuestionScreen(item: item)));
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.pushNamed(context, '/newQuestion');
        },
        child: Icon(Icons.add),
      ),
    );
  }
}
