package main

import (
	"bufio"
	"html"
	"log"
	"os"
	"strconv"
	"strings"
)

func main() {
	input, err := os.Open("in.txt")

	if err != nil {
		panic(err)
	}

	output, err := os.Create("out.txt")

	if err != nil {
		panic(err)
	}

	scanner := bufio.NewScanner(input)

	for scanner.Scan() {
		line := scanner.Text()

		line = html.UnescapeString(line)
		line = strings.Replace(line, "\r\n", "\n", -1)
		line = strings.Replace(line, "\n", " ", -1)
		line = strings.Replace(line, "`", "'", -1)
		line = strings.Replace(line, `""""`, "", -1)
		line = strings.ToLower(line)
		line = strings.Trim(line, `'";`)

		line = strings.Replace(line, `"`, `\"`, -1)
		line = `"` + line + `"`
		line, err = strconv.Unquote(line)

		if err != nil {
			log.Println("Line skipped")
			continue
		}

		line = strings.TrimSpace(line)

		if len(line) == 0 {
			continue
		}

		_, err = output.WriteString(line + "\n")

		if err != nil {
			panic(err)
		}
	}

	err = scanner.Err()

	if err != nil {
		panic(err)
	}
}
