import 'package:client/model/research_item.dart';
import 'package:client/screens/home_screen.dart';
import 'package:client/screens/research_question_screen.dart';
import 'package:flutter/material.dart';
import 'package:client/provider/providers.dart';

class NewQuestionScreen extends StatefulWidget {
  NewQuestionScreen({super.key});
  final ResearchItem item = ResearchItem();

  @override
  _NewQuestionScreenState createState() => _NewQuestionScreenState();
}

class _NewQuestionScreenState extends State<NewQuestionScreen> {
  final _questionController = TextEditingController();
  bool _isButtonEnabled = false;
  final List<String> _interests = ['AI', 'Machine Learning', 'Data Science', 'Robotics'];
  String? _selectedInterest;
  String _selectedFilter = 'Last Year';
  final List<String> _filters = ['Last Week', 'Last Month', 'Last Year'];

  @override
  void initState() {
    super.initState();
    _questionController.addListener(() {
      setState(() {
        _isButtonEnabled = _questionController.text.isNotEmpty;
      });
    });
  }

  @override
  void dispose() {
    _questionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('New Research Question'),
        leading: IconButton(
          icon: Icon(Icons.arrow_back),
          onPressed: () {
            Navigator.pop(context);
            Navigator.push(context, MaterialPageRoute(builder: (context) => HomeScreen()));
          },
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          children: [
            TextField(
              controller: _questionController,
              decoration: InputDecoration(labelText: 'Research Question'),
            ),
            // List of potential interests
            Expanded(
              child: ListView.builder(
                itemCount: _interests.length,
                itemBuilder: (context, index) {
                  final interest = _interests[index];
                  return RadioListTile<String>(
                    title: Text(interest),
                    value: interest,
                    groupValue: _selectedInterest,
                    onChanged: (String? value) {
                      setState(() {
                        _selectedInterest = value;
                      });
                    },
                  );
                },
              ),
            ),
            // Dropdown menu for filtering
            DropdownButton<String>(
              value: _selectedFilter,
              items: _filters.map((String filter) {
                return DropdownMenuItem<String>(
                  value: filter,
                  child: Text(filter),
                );
              }).toList(),
              onChanged: (String? newValue) {
                setState(() {
                  _selectedFilter = newValue!;
                });
              },
            ),
            Spacer(),
            Container(
              margin: EdgeInsets.only(bottom: 24),
              child: ElevatedButton(
                onPressed: _isButtonEnabled
                    ? () {
                        widget.item.question = _questionController.text;
                        widget.item.interests = _selectedInterest != null ? [_selectedInterest!] : [];
                        widget.item.timeRange = _selectedFilter.contains("Year") ? "year" : _selectedFilter.contains("Month") ? "month" : "week";
                        researchItems.add(widget.item);
                        Navigator.pop(context);
                        Navigator.push(context, MaterialPageRoute(builder: (context) => ResearchQuestionScreen(item: widget.item)));
                        // Send GET request to server and navigate to research question screen
                      }
                    : null,
                child: Text('Ask AI'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
