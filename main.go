package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/bwmarrin/discordgo"
	"github.com/joho/godotenv"
)

type pinRequest struct {
	ChannelID string
	MessageID string
}

var (
	token            string
	confirmCap       int
	messageVoteCount = make(map[string]int)
	messageToPin     = make(map[string]pinRequest)
	// CORRECTED: Storing emojis in the 'name:id' format required by discordgo
	numberEmojis = []string{
		"1_:1404868671704272906",
		"2_:1404868687969910986",
		"3_:1404868696123375757",
		"4_:1404868709150888167",
		"5_:1404868718064042004",
		"6_:1404868725416661064",
		"7_:1404868732400173148",
		"8_:1404868741807996978",
		"9_:1404868751387660428",
		"10:1404868763710652547",
	}
)

func ready(s *discordgo.Session, event *discordgo.Ready) {
	log.Printf("Bot is online as: %s#%s", s.State.User.Username, s.State.User.Discriminator)
}

func main() {
	godotenv.Load()

	token = os.Getenv("TOKEN")
	if token == "" {
		log.Fatal("No token provided. Please set TOKEN environment variable.")
	}

	capStr := os.Getenv("CONFIRM_CAP")
	if capStr == "" {
		log.Fatal("No CONFIRM_CAP provided. Please set CONFIRM_CAP environment variable.")
	}

	var err error
	confirmCap, err = strconv.Atoi(capStr)
	if err != nil {
		log.Fatalf("Error converting CONFIRM_CAP to integer: %v", err)
	}

	// CORRECTED: confirmCap must be between 1 and 10 to be a valid index for numberEmojis
	if confirmCap > 10 || confirmCap < 1 {
		log.Fatal("CONFIRM_CAP must be between 1 and 10")
	}

	log.Println("Creating Discord session...")
	dg, err := discordgo.New("Bot " + token)
	if err != nil {
		log.Fatalf("Error creating Discord session: %v", err)
	}

	dg.AddHandler(ready)
	dg.AddHandler(messageCreate)
	dg.AddHandler(reactionAdd)

	dg.Identify.Intents = discordgo.IntentsGuildMessages | discordgo.IntentsGuildMessageReactions

	log.Println("Opening websocket connection...")
	err = dg.Open()
	if err != nil {
		log.Fatalf("Error opening connection: %v", err)
	}

	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-sc

	dg.Close()
}

func messageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	if m.Author.ID == s.State.User.ID {
		return
	}

	isMentioned := false
	for _, user := range m.Mentions {
		if user.ID == s.State.User.ID {
			isMentioned = true
			break
		}
	}

	if isMentioned && m.MessageReference != nil {
		referencedMessage := m.MessageReference

		messageVoteCount[m.ID] = 0
		messageToPin[m.ID] = pinRequest{
			ChannelID: referencedMessage.ChannelID,
			MessageID: referencedMessage.MessageID,
		}
		s.MessageReactionAdd(m.ChannelID, m.ID, "✅")
		s.MessageReactionAdd(m.ChannelID, m.ID, "slash:1404872667189743697")

		// CORRECTED: Use translateNumber with confirmCap and handle potential error
		numberEmoji, err := translateNumber(confirmCap)
		if err != nil {
			log.Printf("Error translating number to emoji: %v", err)
		} else {
			err = s.MessageReactionAdd(m.ChannelID, m.ID, numberEmoji)
			if err != nil {
				// This log will show if adding the custom emoji fails
				log.Printf("Failed to add custom emoji reaction '%s': %v", numberEmoji, err)
			}
		}
	}
}

func reactionAdd(s *discordgo.Session, r *discordgo.MessageReactionAdd) {
	if r.UserID == s.State.User.ID {
		return
	}

	// Check if the reaction is one of the number emojis
	isNumberEmoji := false
	for _, emoji := range numberEmojis {
		if r.Emoji.APIName() == emoji {
			isNumberEmoji = true
			break
		}
	}

	if isNumberEmoji {
		if _, ok := messageVoteCount[r.MessageID]; ok {
			messageVoteCount[r.MessageID]++
			if messageVoteCount[r.MessageID] >= confirmCap {
				targetMessage, exists := messageToPin[r.MessageID]
				if exists {
					err := s.ChannelMessagePin(targetMessage.ChannelID, targetMessage.MessageID)
					if err != nil {
						fmt.Println("Error pinning message:", err)
					}
					// Clean up after pinning
					delete(messageVoteCount, r.MessageID)
					delete(messageToPin, r.MessageID)
				}
			}
		}
	}
}

func translateNumber(num int) (string, error) {
	if num < 1 || num > 10 {
		return "", fmt.Errorf("number out of range: %d", num)
	}
	return numberEmojis[num-1], nil
}
