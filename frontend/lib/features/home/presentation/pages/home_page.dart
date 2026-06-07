import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Form Builder Home'),
      ),
      body: const Center(
        child: Text(
          'Welcome to the Form Builder Application!',
          style: TextStyle(fontSize: 20),
        ),
      ),
    );
  }
}
