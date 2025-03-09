import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/new_question_screen.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Research Assistant',
      theme: ThemeData(
        primaryColor: Colors.purple.shade100,
        colorScheme: ColorScheme.fromSwatch().copyWith(
          secondary: Colors.deepPurple,
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: Colors.purple.shade100,
        ),
        floatingActionButtonTheme: FloatingActionButtonThemeData(
          backgroundColor: Colors.deepPurple,
        ),
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => HomeScreen(),
        // '/researchQuestion': (context) => ResearchQuestionScreen(),
        '/newQuestion': (context) => NewQuestionScreen(),
      },
    );
  }
}
